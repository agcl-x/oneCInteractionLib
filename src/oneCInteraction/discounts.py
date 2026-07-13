from datetime import datetime
from .log import log_sys
from . import structures

class DiscountsManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def get_active_groups(self, s_discount_type_codeIn: str = None) -> list:
        """Retrieves and groups active nomenclature discounts into DiscountGroup structures.
        If s_discount_type_codeIn is specified, only returns groups matching that discount type code.
        """
        if not self.c_v8:
            log_sys("Failed to get active discount groups: No connection to 1C.", 1)
            return []

        try:
            if s_discount_type_codeIn is not None:
                log_sys(f"Fetching active nomenclature discounts from 1C filtered by type code: '{s_discount_type_codeIn}'...")
            else:
                log_sys("Fetching active nomenclature discounts from 1C...")
            query = self.c_v8.NewObject("Query")
            
            query_text = """
                SELECT
                    Скидки.Регистратор.Номер КАК DocNumber,
                    ISNULL(Скидки.Регистратор.ТипСкидкиНаценки.Наименование, "Знижка") КАК DiscountName,
                    ISNULL(Скидки.Регистратор.ТипСкидкиНаценки.Код, "") КАК DiscountTypeCode,
                    Скидки.ПроцентСкидкиНаценки КАК DiscountPercent,
                    Скидки.Номенклатура КАК ProductRef,
                    Скидки.Номенклатура.Код КАК ProductCode,
                    Скидки.Номенклатура.Наименование КАК ProductName,
                    ISNULL(Скидки.ХарактеристикаНоменклатуры.Наименование, "") AS CharName,
                    ISNULL(Скидки.Регистратор.Комментарий, "") AS DocComment
                FROM
                    РегистрСведений.СкидкиНаценкиНоменклатуры.СрезПоследних(&CurrentDate, ) КАК Скидки
                WHERE
                    Скидки.ПроцентСкидкиНаценки > 0
            """
            
            if s_discount_type_codeIn is not None:
                query_text += "\n                    AND Скидки.Регистратор.ТипСкидкиНаценки.Код = &DiscountTypeCode"
                
            query.Text = query_text
            
            c_currDate = datetime.now(self.c_connection.tz_kiev).replace(tzinfo=None)
            query.SetParameter("CurrentDate", c_currDate)
            if s_discount_type_codeIn is not None:
                query.SetParameter("DiscountTypeCode", s_discount_type_codeIn)

            c_result = query.Execute()
            if c_result is None or c_result.IsEmpty():
                log_sys("No active discounts found in register.")
                return []

            # Group the results by (DocNumber, DiscountTypeCode, DiscountPercent)
            d_groups = {} # {(doc_num, type_code, percent): {"name": str, "comment": str, "items": list}}

            c_selection = c_result.Select()
            while c_selection.Next():
                s_doc_number = self.c_v8.String(c_selection.DocNumber)
                s_type_code = self.c_v8.String(c_selection.DiscountTypeCode)
                n_percent = float(c_selection.DiscountPercent)
                s_name = self.c_v8.String(c_selection.DiscountName)
                s_comment = self.c_v8.String(c_selection.DocComment)

                s_product_code = self.c_v8.String(c_selection.ProductCode)
                s_product_name = self.c_v8.String(c_selection.ProductName)
                s_char_name = self.c_v8.String(c_selection.CharName)
                s_product_uuid = self.c_v8.String(c_selection.ProductRef.UUID())

                key = (s_doc_number, s_type_code, n_percent)
                if key not in d_groups:
                    d_groups[key] = {
                        "name": s_name,
                        "comment": s_comment,
                        "items": []
                    }

                d_groups[key]["items"].append({
                    "code": s_product_code,
                    "name": s_product_name,
                    "uuid": s_product_uuid,
                    "char_name": s_char_name if s_char_name else None
                })

            # Convert dictionary groups into structures.DiscountGroup objects
            l_discount_groups = []
            type_counters = {}
            for (s_doc_number, s_type_code, n_percent), d_group_data in d_groups.items():
                s_comment = d_group_data["comment"].strip()
                if s_comment:
                    s_display_name = s_comment
                else:
                    s_type_name = d_group_data["name"]
                    type_counters[s_type_code] = type_counters.get(s_type_code, 0) + 1
                    s_display_name = f"{s_type_name} {type_counters[s_type_code]}"

                l_discount_groups.append(structures.DiscountGroup(
                    s_nameIn=s_display_name,
                    s_document_numberIn=s_doc_number,
                    s_discount_type_codeIn=s_type_code,
                    n_discount_percentIn=n_percent,
                    l_nomenclaturesIn=d_group_data["items"]
                ))

            log_sys(f"Successfully retrieved {len(l_discount_groups)} active discount groups.")
            return l_discount_groups

        except Exception as e:
            log_sys(f"Error in DiscountsManager.get_active_groups: {e}", 1)
            return []
