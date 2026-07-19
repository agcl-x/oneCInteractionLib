from .log import log_sys
from . import structures

class PropertiesManager:
    """Manages reading, writing, and deleting product properties in 1C (РегистрСведений.ЗначенияСвойствОбъектов)."""

    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def _resolve_product_ref(self, c_productIn):
        """Resolves a product input (Nomenclature, COM Ref, or string ID/code/article) into a 1C COM Reference."""
        if not self.c_v8 or c_productIn is None:
            return None

        # 1. If it's a Nomenclature object
        if hasattr(c_productIn, "s_uuid") and c_productIn.s_uuid:
            try:
                v8_uuid = self.c_v8.NewObject("UUID", c_productIn.s_uuid)
                c_ref = self.c_v8.Catalogs.Номенклатура.GetRef(v8_uuid)
                if not c_ref.IsEmpty():
                    return c_ref
            except Exception:
                pass
            
            # Fallback to article or code if UUID fails
            c_productIn = c_productIn.s_article or c_productIn.s_code

        # 2. If it's a string identifier (UUID, article, or code)
        if isinstance(c_productIn, str):
            s_val = c_productIn.strip()
            
            # Try UUID first
            if len(s_val) == 36 and "-" in s_val:
                try:
                    v8_uuid = self.c_v8.NewObject("UUID", s_val)
                    c_ref = self.c_v8.Catalogs.Номенклатура.GetRef(v8_uuid)
                    if not c_ref.IsEmpty():
                        return c_ref
                except Exception:
                    pass

            # Query by code or article
            try:
                c_query = self.c_v8.NewObject("Query")
                c_query.Text = """
                    SELECT TOP 1 Ссылка FROM Справочник.Номенклатура 
                    WHERE (Код = &Val OR Артикул = &Val) AND ЭтоГруппа = ЛОЖЬ AND ПометкаУдаления = ЛОЖЬ
                """
                c_query.SetParameter("Val", s_val)
                c_res = c_query.Execute()
                if c_res is not None and not c_res.IsEmpty():
                    c_sel = c_res.Select()
                    c_sel.Next()
                    return c_sel.Ссылка
            except Exception as e:
                log_sys(f"Error resolving product reference by string: {e}", 1)
                
            return None

        # 3. Otherwise assume it's already a 1C COM Reference
        return c_productIn

    def _resolve_property_ref(self, s_nameOrCodeIn: str, c_productRef):
        """Resolves a property name or code to a 1C PlanOfCharacteristicTypes.СвойстваОбъектов reference."""
        if not self.c_v8 or not s_nameOrCodeIn:
            return None, False

        prop_name_or_code = s_nameOrCodeIn.strip()
        
        try:
            # Query by Name or Code in ПланыВидовХарактеристик.СвойстваОбъектов
            q_prop = self.c_v8.NewObject("Query")
            q_prop.Text = """
                SELECT
                    Свойства.Ссылка AS Ref,
                    Свойства.ПометкаУдаления AS DeletionMark,
                    Свойства.НазначениеСвойства AS Assignment,
                    ISNULL(Свойства.НазначениеСвойства.Наименование, "") AS AssignmentName
                FROM
                    ПланВидовХарактеристик.СвойстваОбъектов AS Свойства
                WHERE
                    Свойства.Наименование = &SearchVal OR Свойства.Код = &SearchVal
            """
            q_prop.SetParameter("SearchVal", prop_name_or_code)
            res_prop = q_prop.Execute()

            candidates = []
            if not res_prop.IsEmpty():
                sel_p = res_prop.Select()
                while sel_p.Next():
                    candidates.append({
                        "ref": sel_p.Ref,
                        "is_deleted": bool(sel_p.DeletionMark),
                        "assignment": sel_p.Assignment,
                        "assignment_name": str(sel_p.AssignmentName)
                    })

            if not candidates:
                return None, False

            chosen_cand = None

            # 1. Match specific product's parent folders (closest parent first)
            parent_refs = []
            try:
                current_parent = c_productRef.Родитель
                while current_parent and not current_parent.IsEmpty():
                    parent_refs.append(current_parent)
                    current_parent = current_parent.Родитель
            except Exception:
                pass

            def is_equal_1c(ref1, ref2):
                if not ref1 or not ref2:
                    return False
                try:
                    return str(self.c_v8.String(ref1.UUID())) == str(self.c_v8.String(ref2.UUID()))
                except Exception:
                    return str(ref1) == str(ref2)

            for p_ref in parent_refs:
                for cand in candidates:
                    if is_equal_1c(cand["assignment"], p_ref):
                        chosen_cand = cand
                        break
                if chosen_cand:
                    break

            # 2. General "Номенклатура" assignment
            if not chosen_cand:
                for cand in candidates:
                    assign_name = cand["assignment_name"].lower()
                    if "номенклатура" in assign_name:
                        chosen_cand = cand
                        break

            # 3. Fallback to first non-deleted candidate
            if not chosen_cand:
                for cand in candidates:
                    if not cand["is_deleted"]:
                        chosen_cand = cand
                        break

            # 4. Ultimate fallback to first candidate
            if not chosen_cand:
                chosen_cand = candidates[0]

            return chosen_cand["ref"], chosen_cand["is_deleted"]

        except Exception as e:
            log_sys(f"Error resolving property '{s_nameOrCodeIn}': {e}", 1)
            return None, False

    def get_assigned_properties(self, c_productIn) -> list:
        """
        Retrieves properties assigned to a specific product.
        Returns a list of structures.Property objects.
        """
        if not self.c_v8:
            log_sys("Failed to get assigned properties: No connection to 1C.", 1)
            return []

        c_productRef = self._resolve_product_ref(c_productIn)
        if c_productRef is None or c_productRef.IsEmpty():
            log_sys(f"Failed to get properties: Product reference could not be resolved for input {c_productIn}", 1)
            return []

        l_properties = []
        try:
            c_propQuery = self.c_v8.NewObject("Query")
            c_propQuery.Text = """
                SELECT
                    Properties.Свойство.Наименование AS PropName,
                    Properties.Значение.Наименование AS ValName
                FROM
                    РегистрСведений.ЗначенияСвойствОбъектов AS Properties
                WHERE
                    Properties.Объект = &ProductRef
            """
            c_propQuery.SetParameter("ProductRef", c_productRef)
            c_propRes = c_propQuery.Execute()
            if c_propRes is not None and not c_propRes.IsEmpty():
                c_sel = c_propRes.Select()
                while c_sel.Next():
                    l_properties.append(structures.Property(c_sel.PropName, c_sel.ValName))
        except Exception as e:
            log_sys(f"Error fetching properties: {e}", 1)

        return l_properties

    def write_batch(self, c_productIn, l_propertiesIn: list, b_forceIn: bool = False) -> list:
        """
        Writes/updates multiple properties for a product using a single 1C RecordSet.
        Each property can be a structures.Property object or a dict {"name": "...", "value": "..."}.
        If b_forceIn is True, removes all other product properties (except 'Код') first.
        Returns a list of successfully written properties: [{"name": "...", "value": "..."}].
        """
        if not self.c_v8:
            log_sys("Failed to write properties: No connection to 1C.", 1)
            return []

        c_productRef = self._resolve_product_ref(c_productIn)
        if c_productRef is None or c_productRef.IsEmpty():
            log_sys(f"Failed to write properties: Product reference could not be resolved for input {c_productIn}", 1)
            return []

        written_properties = []
        properties_to_write = []

        # Normalize input list
        normalized_props = []
        for prop in l_propertiesIn:
            if hasattr(prop, "s_name") and hasattr(prop, "s_value"):
                normalized_props.append({"name": prop.s_name, "value": prop.s_value})
            elif isinstance(prop, dict) and "name" in prop and "value" in prop:
                normalized_props.append({"name": prop["name"], "value": prop["value"]})

        for prop in normalized_props:
            prop_name_or_code = prop["name"].strip()
            prop_value = prop["value"].strip()
            if not prop_name_or_code or not prop_value:
                continue

            if prop_name_or_code.lower() == "код":
                log_sys("Skipped: Property name/code is 'Код'. Cannot modify.", 1)
                continue

            prop_ref, is_deleted = self._resolve_property_ref(prop_name_or_code, c_productRef)
            
            if is_deleted:
                log_sys(f"Skipped: Property '{prop_name_or_code}' is marked for deletion in 1C.", 1)
                continue

            try:
                # 1. Create Property if not found
                if not prop_ref or prop_ref.IsEmpty():
                    log_sys(f"Property '{prop_name_or_code}' not found. Creating in ПланыВидовХарактеристик.СвойстваОбъектов...")
                    new_prop = self.c_v8.ChartsOfCharacteristicTypes.СвойстваОбъектов.CreateItem()
                    new_prop.Description = prop_name_or_code
                    try:
                        type_descr = self.c_v8.NewObject("TypeDescription", "СправочникСсылка.ЗначенияСвойствОбъектов")
                        new_prop.ТипЗначения = type_descr
                    except Exception as e_type:
                        log_sys(f"Warning setting value type for property '{prop_name_or_code}': {e_type}", 1)
                    new_prop.Write()
                    prop_ref = new_prop.Ref

                # 2. Find or create Value in Справочники.ЗначенияСвойствОбъектов
                val_ref = self.c_v8.Catalogs.ЗначенияСвойствОбъектов.EmptyRef()
                try:
                    q_val = self.c_v8.NewObject("Query")
                    q_val.Text = """
                        SELECT TOP 1
                            Значения.Ссылка AS Ref
                        FROM
                            Справочник.ЗначенияСвойствОбъектов AS Значения
                        WHERE
                            Значения.Наименование = &ValName
                            AND Значения.Владелец = &Owner
                    """
                    q_val.SetParameter("ValName", prop_value)
                    q_val.SetParameter("Owner", prop_ref)
                    res_val = q_val.Execute()
                    if not res_val.IsEmpty():
                        sel_v = res_val.Select()
                        sel_v.Next()
                        val_ref = sel_v.Ref
                except Exception as e_v:
                    log_sys(f"Warning querying value '{prop_value}': {e_v}", 1)

                if val_ref.IsEmpty():
                    log_sys(f"Creating value '{prop_value}' for property '{prop_name_or_code}' in Справочники.ЗначенияСвойствОбъектов...")
                    new_val = self.c_v8.Catalogs.ЗначенияСвойствОбъектов.CreateItem()
                    new_val.Owner = prop_ref
                    new_val.Description = prop_value
                    new_val.Write()
                    val_ref = new_val.Ref

                try:
                    canonical_name = str(self.c_v8.String(prop_ref.Наименование))
                except Exception:
                    canonical_name = prop_name_or_code

                properties_to_write.append({
                    "prop_ref": prop_ref,
                    "val_ref": val_ref,
                    "name": canonical_name,
                    "value": prop_value
                })
                written_properties.append({"name": canonical_name, "value": prop_value})
            except Exception as e:
                log_sys(f"Failed to prepare property '{prop_name_or_code}' for writing to 1C: {e}", 1)

        # Write to register via RecordSet
        if (properties_to_write or b_forceIn) and self.c_v8:
            try:
                record_set = self.c_v8.InformationRegisters.ЗначенияСвойствОбъектов.CreateRecordSet()
                
                filter_obj = record_set.Filter.Объект
                try:
                    filter_obj.Set(c_productRef)
                except Exception:
                    try:
                        filter_obj.Установить(c_productRef)
                    except Exception:
                        try:
                            filter_obj.Value = c_productRef
                            filter_obj.Use = True
                        except Exception:
                            filter_obj.Значение = c_productRef
                            filter_obj.Использование = True

                record_set.Read()

                # Build existing records map
                existing_records = {}
                count = 0
                try:
                    count = record_set.Count()
                except Exception:
                    try:
                        count = record_set.Количество()
                    except Exception:
                        pass

                if b_forceIn:
                    log_sys("Clearing all existing properties except 'Код'...")
                    for i in range(count - 1, -1, -1):
                        try:
                            rec = record_set.Get(i)
                        except Exception:
                            rec = record_set.Получить(i)

                        if isinstance(rec, (tuple, list)) and len(rec) > 0:
                            rec = rec[0]

                        try:
                            p_name = str(self.c_v8.String(rec.Свойство.Наименование))
                        except Exception:
                            try:
                                p_name = str(rec.Свойство.Наименование)
                            except Exception:
                                p_name = ""

                        if p_name.lower() != "код":
                            try:
                                record_set.Delete(i)
                            except Exception:
                                try:
                                    record_set.Удалить(i)
                                except Exception as e_del:
                                    log_sys(f"Failed to delete record at index {i}: {e_del}", 1)

                    # Recompute count
                    try:
                        count = record_set.Count()
                    except Exception:
                        try:
                            count = record_set.Количество()
                        except Exception:
                            count = 0

                for i in range(count):
                    try:
                        rec = record_set.Get(i)
                    except Exception:
                        rec = record_set.Получить(i)

                    if isinstance(rec, (tuple, list)):
                        if len(rec) > 0:
                            rec = rec[0]
                        else:
                            continue

                    try:
                        p_uuid = str(self.c_v8.String(rec.Свойство.UUID()))
                    except Exception:
                        p_uuid = str(rec.Свойство)
                    existing_records[p_uuid] = rec

                for prop_info in properties_to_write:
                    p_ref = prop_info["prop_ref"]
                    v_ref = prop_info["val_ref"]
                    p_name = prop_info["name"]
                    p_val = prop_info["value"]

                    try:
                        p_uuid = str(self.c_v8.String(p_ref.UUID()))
                    except Exception:
                        p_uuid = str(p_ref)

                    if p_uuid in existing_records:
                        rec = existing_records[p_uuid]
                        if isinstance(rec, (tuple, list)):
                            if len(rec) > 0:
                                rec = rec[0]

                        try:
                            old_val = rec.Значение
                        except Exception:
                            old_val = rec.Value

                        if old_val != v_ref:
                            try:
                                rec.Значение = v_ref
                            except Exception:
                                rec.Value = v_ref
                            log_sys(f"Updated property '{p_name}' = '{p_val}' in record set.")
                        else:
                            log_sys(f"Property '{p_name}' already set to '{p_val}'. Skipping update.")
                    else:
                        try:
                            new_rec = record_set.Add()
                        except Exception:
                            new_rec = record_set.Добавить()

                        if isinstance(new_rec, (tuple, list)):
                            if len(new_rec) > 0:
                                new_rec = new_rec[0]

                        new_rec.Объект = c_productRef
                        new_rec.Свойство = p_ref
                        try:
                            new_rec.Значение = v_ref
                        except Exception:
                            new_rec.Value = v_ref
                        log_sys(f"Added property '{p_name}' = '{p_val}' to record set.")

                try:
                    record_set.Write(True)
                except Exception:
                    record_set.Записать(True)
                log_sys("Successfully wrote properties to 1C register.")
            except Exception as e_write:
                log_sys(f"Failed to write record set to 1C: {e_write}", 1)
                written_properties = []

        return written_properties

    def write(self, c_productIn, s_propertyNameOrCodeIn: str, s_propertyValueIn: str) -> bool:
        """
        Writes or updates a single property value for a product.
        Returns True if successful, False otherwise.
        """
        res = self.write_batch(c_productIn, [{"name": s_propertyNameOrCodeIn, "value": s_propertyValueIn}], b_forceIn=False)
        return len(res) > 0

    def delete(self, c_productIn, s_propertyNameOrCodeIn: str) -> bool:
        """
        Removes a specific property from a product in 1C register.
        Returns True if successful, False otherwise.
        """
        if not self.c_v8:
            log_sys("Failed to delete property: No connection to 1C.", 1)
            return False

        c_productRef = self._resolve_product_ref(c_productIn)
        if c_productRef is None or c_productRef.IsEmpty():
            log_sys(f"Failed to delete property: Product reference could not be resolved for input {c_productIn}", 1)
            return False

        prop_ref, is_deleted = self._resolve_property_ref(s_propertyNameOrCodeIn, c_productRef)
        if prop_ref is None or prop_ref.IsEmpty():
            log_sys(f"Property '{s_propertyNameOrCodeIn}' not found. Skipping deletion.", 1)
            return False

        try:
            record_set = self.c_v8.InformationRegisters.ЗначенияСвойствОбъектов.CreateRecordSet()
            
            filter_obj = record_set.Filter.Объект
            try:
                filter_obj.Set(c_productRef)
            except Exception:
                try:
                    filter_obj.Установить(c_productRef)
                except Exception:
                    try:
                        filter_obj.Value = c_productRef
                        filter_obj.Use = True
                    except Exception:
                        filter_obj.Значение = c_productRef
                        filter_obj.Использование = True

            record_set.Read()

            # Find and delete
            count = 0
            try:
                count = record_set.Count()
            except Exception:
                try:
                    count = record_set.Количество()
                except Exception:
                    pass

            deleted = False
            
            try:
                target_uuid = str(self.c_v8.String(prop_ref.UUID()))
            except Exception:
                target_uuid = str(prop_ref)

            for i in range(count - 1, -1, -1):
                try:
                    rec = record_set.Get(i)
                except Exception:
                    rec = record_set.Получить(i)

                if isinstance(rec, (tuple, list)) and len(rec) > 0:
                    rec = rec[0]

                try:
                    p_uuid = str(self.c_v8.String(rec.Свойство.UUID()))
                except Exception:
                    p_uuid = str(rec.Свойство)

                if p_uuid == target_uuid:
                    try:
                        record_set.Delete(i)
                    except Exception:
                        try:
                            record_set.Удалить(i)
                        except Exception as e_del:
                            log_sys(f"Failed to delete record at index {i}: {e_del}", 1)
                            return False
                    deleted = True
                    break

            if deleted:
                try:
                    record_set.Write(True)
                except Exception:
                    record_set.Записать(True)
                log_sys(f"Successfully deleted property '{s_propertyNameOrCodeIn}' for product.")
                return True
            else:
                log_sys(f"Property '{s_propertyNameOrCodeIn}' was not set on product. Skipping deletion.")
                return True
        except Exception as e:
            log_sys(f"Failed to delete property '{s_propertyNameOrCodeIn}': {e}", 1)
            return False

    def get_all_definitions(self) -> list:
        """
        Retrieves definitions of all active properties in 1C PlanOfCharacteristicTypes.СвойстваОбъектов.
        Returns a list of dictionaries: [{"name": "...", "code": "...", "assignment": "...", "deleted": False}].
        """
        if not self.c_v8:
            log_sys("Failed to retrieve property definitions: No connection to 1C.", 1)
            return []

        properties_metadata = []
        try:
            query = self.c_v8.NewObject("Query")
            query.Text = """
                SELECT
                    Свойства.Наименование AS Name,
                    Свойства.Код AS Code,
                    Свойства.ПометкаУдаления AS DeletionMark,
                    ISNULL(Свойства.НазначениеСвойства.Наименование, "") AS AssignmentName
                FROM
                    ПланВидовХарактеристик.СвойстваОбъектов AS Свойства
                WHERE
                    Свойства.ПометкаУдаления = ЛОЖЬ
                ORDER BY
                    Name
            """
            res = query.Execute()
            if not res.IsEmpty():
                sel = res.Select()
                while sel.Next():
                    properties_metadata.append({
                        "name": str(sel.Name).strip(),
                        "code": str(sel.Code).strip(),
                        "assignment": str(sel.AssignmentName).strip() if sel.AssignmentName else "General",
                        "deleted": bool(sel.DeletionMark)
                    })
        except Exception as e:
            log_sys(f"Error querying property definitions: {e}", 1)

        return properties_metadata
