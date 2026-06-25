import os
from datetime import datetime
from .log import log_sys
from . import structures

class NomenclatureManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def get(self, s_articleIn: str = "", s_nameIn: str = "", s_codeIn: str = ""):
        """Retrieves details of a single Nomenclature item by its article, name, or code."""
        if not self.c_v8:
            log_sys("Failed to get Nomenclature: No connection to 1C. Returning None", 1)
            return None

        log_sys("Trying to get Nomenclature...")
        c_query = self.c_v8.NewObject("Query")
        c_query.Text = """
            SELECT TOP 1 
                Ref, 
                Наименование AS Name, 
                Код AS Code,
                Артикул AS Article, 
                ISNULL(ДополнительноеОписаниеНоменклатуры, "") AS FullDescription,
                ISNULL(НаименованиеПолное, "") AS FullName,
                ISNULL(ЕдиницаХраненияОстатков.Наименование, "шт.") AS Unit
            FROM Catalog.Номенклатура
            WHERE Код = &Code OR Артикул = &Article OR Наименование = &Name
        """
        c_query.SetParameter("Code", s_codeIn)
        c_query.SetParameter("Article", s_articleIn)
        c_query.SetParameter("Name", s_nameIn)

        c_result = c_query.Execute()
        if c_result is None or c_result.IsEmpty():
            log_sys("Nomenclature not found. Returning None", 1)
            return None

        c_selection = c_result.Select()
        c_selection.Next()
        
        s_description = self.c_v8.String(c_selection.FullDescription)
        if not s_description:
            s_description = self.c_v8.String(c_selection.FullName)

        log_sys(f"Nomenclature found: Name='{c_selection.Name}', Article='{c_selection.Article}'")
        return self._fetch_details(
            c_selection.Ref, 
            c_selection.Name, 
            c_selection.Article, 
            s_description,
            getattr(c_selection, "Unit", "шт."),
            self.c_v8.String(c_selection.Ref.UUID()),
            self.c_v8.String(c_selection.Code)
        )

    def _fetch_batch_details(self, l_productRefsIn: list) -> dict:
        """Batch fetches prices and stock quantities for a list of product references."""
        if not self.c_v8 or not l_productRefsIn:
            return {}

        log_sys(f"Batch fetching prices and stocks for {len(l_productRefsIn)} items...")
        
        c_productRefsV8 = self.c_v8.NewObject("ValueList")
        for c_ref in l_productRefsIn:
            c_productRefsV8.Add(c_ref)

        c_charQuery = self.c_v8.NewObject("Query")
        c_charQuery.Text = """
            SELECT 
                MainTable.Ссылка AS ProductRef,
                MainTable.Код AS ProductCode,
                Chars.Ссылка AS CharRef,
                ISNULL(Chars.Наименование, "Без характеристики") AS CharName, 
                ISNULL(Stocks.Склад.Наименование, "Невідомий склад") AS WarehouseName, 
                ВЫБОР 
                    КОГДА ISNULL(RetailPrices.Цена, 0) > 0 ТОГДА RetailPrices.Цена 
                    ИНАЧЕ ISNULL(GeneralRetailPrices.Цена, 0) 
                КОНЕЦ AS RetailPrice,
                ВЫБОР 
                    КОГДА ISNULL(WholesalePrices.Цена, 0) > 0 ТОГДА WholesalePrices.Цена 
                    ИНАЧЕ ISNULL(GeneralWholesalePrices.Цена, 0) 
                КОНЕЦ AS WholesalePrice,
                ВЫБОР 
                    КОГДА ISNULL(PurchasePrices.Цена, 0) > 0 ТОГДА PurchasePrices.Цена 
                    ИНАЧЕ ISNULL(GeneralPurchasePrices.Цена, 0) 
                КОНЕЦ AS PurchasePrice,
                ISNULL(Stocks.КоличествоОстаток, 0) AS Quantity
            FROM Справочник.Номенклатура AS MainTable
            LEFT JOIN Справочник.ХарактеристикиНоменклатуры AS Chars
                ON Chars.Владелец = MainTable.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура В (&ProductRefs) AND ТипЦен = &RetailPriceType) AS RetailPrices
                ON RetailPrices.Номенклатура = MainTable.Ссылка AND RetailPrices.ХарактеристикаНоменклатуры = Chars.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура В (&ProductRefs) AND ТипЦен = &WholesalePriceType) AS WholesalePrices
                ON WholesalePrices.Номенклатура = MainTable.Ссылка AND WholesalePrices.ХарактеристикаНоменклатуры = Chars.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура В (&ProductRefs) AND ТипЦен = &PurchasePriceType) AS PurchasePrices
                ON PurchasePrices.Номенклатура = MainTable.Ссылка AND PurchasePrices.ХарактеристикаНоменклатуры = Chars.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура В (&ProductRefs) AND ТипЦен = &RetailPriceType AND ХарактеристикаНоменклатуры = ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка)) AS GeneralRetailPrices
                ON GeneralRetailPrices.Номенклатура = MainTable.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура В (&ProductRefs) AND ТипЦен = &WholesalePriceType AND ХарактеристикаНоменклатуры = ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка)) AS GeneralWholesalePrices
                ON GeneralWholesalePrices.Номенклатура = MainTable.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура В (&ProductRefs) AND ТипЦен = &PurchasePriceType AND ХарактеристикаНоменклатуры = ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка)) AS GeneralPurchasePrices
                ON GeneralPurchasePrices.Номенклатура = MainTable.Ссылка
            LEFT JOIN РегистрНакопления.ТоварыНаСкладах.Остатки(&CurrentDate, Номенклатура В (&ProductRefs)) AS Stocks
                ON Stocks.Номенклатура = MainTable.Ссылка AND Stocks.ХарактеристикаНоменклатуры = ISNULL(Chars.Ссылка, ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка))
            WHERE
                MainTable.Ссылка В (&ProductRefs)
                AND (
                    (Chars.Ссылка ЕСТЬ НЕ NULL)
                    OR (NOT MainTable.Ссылка В (SELECT Владелец FROM Справочник.ХарактеристикиНоменклатуры WHERE Владелец В (&ProductRefs)))
                )
        """

        c_retailPtRef = self.c_connection.get_price_type_ref("Розничная")
        c_wholesalePtRef = self.c_connection.get_price_type_ref("Оптовая")
        c_purchasePtRef = self.c_connection.get_price_type_ref("Закупочная")
        c_currDate = datetime.now(self.c_connection.tz_kiev).replace(tzinfo=None)

        c_charQuery.SetParameter("ProductRefs", c_productRefsV8)
        c_charQuery.SetParameter("RetailPriceType", c_retailPtRef)
        c_charQuery.SetParameter("WholesalePriceType", c_wholesalePtRef)
        c_charQuery.SetParameter("PurchasePriceType", c_purchasePtRef)
        c_charQuery.SetParameter("CurrentDate", c_currDate)

        d_batchData = {} # {product_uuid: {char_name: data}}

        try:
            c_charResult = c_charQuery.Execute()
            if c_charResult is not None and not c_charResult.IsEmpty():
                c_charSel = c_charResult.Select()
                while c_charSel.Next():
                    s_productUuid = self.c_v8.String(c_charSel.ProductRef.UUID())
                    c_charRef = c_charSel.CharRef
                    s_charName = c_charSel.CharName if c_charSel.CharName != "Без характеристики" else "NULL"
                    s_warehouseName = c_charSel.WarehouseName
                    n_qty = c_charSel.Quantity
                    n_retailP = float(c_charSel.RetailPrice)
                    n_wholesaleP = float(c_charSel.WholesalePrice)
                    n_purchaseP = float(c_charSel.PurchasePrice)

                    if s_productUuid not in d_batchData:
                        d_batchData[s_productUuid] = {}
                    
                    if s_charName not in d_batchData[s_productUuid]:
                        d_batchData[s_productUuid][s_charName] = {
                            "ref": c_charRef,
                            "retail": n_retailP,
                            "wholesale": n_wholesaleP,
                            "purchase": n_purchaseP,
                            "stocks": {}
                        }
                    
                    if s_warehouseName != "Невідомий склад" or n_qty != 0:
                        d_batchData[s_productUuid][s_charName]["stocks"][s_warehouseName] = n_qty

        except Exception as e:
            log_sys(f"Error in batch query execution: {e}", 1)

        return d_batchData

    def _fetch_batch_image_metadata(self, l_productRefsIn: list) -> dict:
        """Batch fetches image references (UUIDs) for a list of product references."""
        if not self.c_v8 or not l_productRefsIn:
            return {}
            
        log_sys(f"Batch fetching image metadata for {len(l_productRefsIn)} items...")
        c_refsV8 = self.c_v8.NewObject("ValueList")
        for c_ref in l_productRefsIn:
            c_refsV8.Add(c_ref)
            
        c_query = self.c_v8.NewObject("Query")
        c_query.Text = """
            SELECT Объект AS ProductRef, Ссылка AS ImageRef
            FROM Справочник.ХранилищеДополнительнойИнформации
            WHERE Объект В (&ProductRefs) AND ПометкаУдаления = ЛОЖЬ
        """
        c_query.SetParameter("ProductRefs", c_refsV8)
        
        d_batchImages = {}
        try:
            c_res = c_query.Execute()
            if not c_res.IsEmpty():
                c_sel = c_res.Select()
                while c_sel.Next():
                    s_productUuid = self.c_v8.String(c_sel.ProductRef.UUID())
                    s_imageUuid = self.c_v8.String(c_sel.ImageRef.UUID())
                    if s_productUuid not in d_batchImages:
                        d_batchImages[s_productUuid] = []
                    d_batchImages[s_productUuid].append(s_imageUuid)
        except Exception as e:
            log_sys(f"Error in batch image metadata: {e}", 1)
            
        return d_batchImages

    def _fetch_details(
        self,
        c_productRefIn,
        s_nameIn: str,
        s_articleIn: str,
        s_descriptionIn: str,
        s_unitIn: str = "шт.",
        s_uuidIn: str = "",
        s_codeIn: str = ""
    ):
        """Fetches details (prices, stock, characteristics) for a single Nomenclature."""
        c_retailPtRef = self.c_connection.get_price_type_ref("Розничная")
        c_wholesalePtRef = self.c_connection.get_price_type_ref("Оптовая")
        c_purchasePtRef = self.c_connection.get_price_type_ref("Закупочная")
        c_currDate = datetime.now(self.c_connection.tz_kiev).replace(tzinfo=None)

        c_charQuery = self.c_v8.NewObject("Query")
        c_charQuery.Text = """
            SELECT 
                Chars.Ссылка AS CharRef,
                ISNULL(Chars.Наименование, "Без характеристики") AS CharName, 
                ISNULL(Stocks.Склад.Наименование, "Невідомий склад") AS WarehouseName, 
                ВЫБОР 
                    КОГДА ISNULL(RetailPrices.Цена, 0) > 0 ТОГДА RetailPrices.Цена 
                    ИНАЧЕ ISNULL(GeneralRetailPrices.Цена, 0) 
                КОНЕЦ AS RetailPrice,
                ВЫБОР 
                    КОГДА ISNULL(WholesalePrices.Цена, 0) > 0 ТОГДА WholesalePrices.Цена 
                    ИНАЧЕ ISNULL(GeneralWholesalePrices.Цена, 0) 
                КОНЕЦ AS WholesalePrice,
                ВЫБОР 
                    КОГДА ISNULL(PurchasePrices.Цена, 0) > 0 ТОГДА PurchasePrices.Цена 
                    ИНАЧЕ ISNULL(GeneralPurchasePrices.Цена, 0) 
                КОНЕЦ AS PurchasePrice,
                ISNULL(Stocks.КоличествоОстаток, 0) AS Quantity
            FROM (SELECT &ProductRef AS Номенклатура) AS MainTable
            LEFT JOIN Справочник.ХарактеристикиНоменклатуры AS Chars
                ON Chars.Владелец = MainTable.Номенклатура
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура = &ProductRef AND ТипЦен = &RetailPriceType) AS RetailPrices
                ON RetailPrices.ХарактеристикаНоменклатуры = Chars.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура = &ProductRef AND ТипЦен = &WholesalePriceType) AS WholesalePrices
                ON WholesalePrices.ХарактеристикаНоменклатуры = Chars.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура = &ProductRef AND ТипЦен = &PurchasePriceType) AS PurchasePrices
                ON PurchasePrices.ХарактеристикаНоменклатуры = Chars.Ссылка
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура = &ProductRef AND ТипЦен = &RetailPriceType AND ХарактеристикаНоменклатуры = ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка)) AS GeneralRetailPrices
                ON ИСТИНА
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура = &ProductRef AND ТипЦен = &WholesalePriceType AND ХарактеристикаНоменклатуры = ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка)) AS GeneralWholesalePrices
                ON ИСТИНА
            LEFT JOIN РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&CurrentDate, Номенклатура = &ProductRef AND ТипЦен = &PurchasePriceType AND ХарактеристикаНоменклатуры = ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка)) AS GeneralPurchasePrices
                ON ИСТИНА
            LEFT JOIN РегистрНакопления.ТоварыНаСкладах.Остатки(&CurrentDate, Номенклатура = &ProductRef) AS Stocks
                ON Stocks.ХарактеристикаНоменклатуры = ISNULL(Chars.Ссылка, ЗНАЧЕНИЕ(Справочник.ХарактеристикиНоменклатуры.ПустаяСсылка))
            WHERE
                (Chars.Ссылка ЕСТЬ НЕ NULL)
                OR (NOT &ProductRef В (SELECT Владелец FROM Справочник.ХарактеристикиНоменклатуры WHERE Владелец = &ProductRef))
        """

        c_charQuery.SetParameter("ProductRef", c_productRefIn)
        c_charQuery.SetParameter("RetailPriceType", c_retailPtRef)
        c_charQuery.SetParameter("WholesalePriceType", c_wholesalePtRef)
        c_charQuery.SetParameter("PurchasePriceType", c_purchasePtRef)
        c_charQuery.SetParameter("CurrentDate", c_currDate)

        try:
            c_charResult = c_charQuery.Execute()
        except Exception as e:
            log_sys(f"Query execution error for article {s_articleIn}: {e}", 1)
            c_charResult = None

        d_tempData = {}

        if c_charResult is not None and not c_charResult.IsEmpty():
            c_charSel = c_charResult.Select()
            while c_charSel.Next():
                try:
                    c_charRef = c_charSel.CharRef
                    s_charName = c_charSel.CharName if c_charSel.CharName != "Без характеристики" else "NULL"
                    s_warehouseName = c_charSel.WarehouseName
                    n_qty = c_charSel.Quantity
                    n_retailPrice = float(c_charSel.RetailPrice)
                    n_wholesalePrice = float(c_charSel.WholesalePrice)
                    n_purchasePrice = float(c_charSel.PurchasePrice)

                    if s_charName not in d_tempData:
                        d_tempData[s_charName] = {
                            "ref": c_charRef,
                            "retail": n_retailPrice,
                            "wholesale": n_wholesalePrice,
                            "purchase": n_purchasePrice,
                            "stocks": {}
                        }

                    # Even if stock is 0, we preserve the price details
                    if s_warehouseName != "Невідомий склад" or n_qty != 0:
                        d_tempData[s_charName]["stocks"][s_warehouseName] = n_qty
                        
                except Exception as e:
                    log_sys(f"Error parsing characteristic row for {s_articleIn}: {e}", 1)

        if not d_tempData:
             log_sys(f"No price or stock data found for article {s_articleIn}", 1)

        l_varieties = []
        for s_charName in sorted(d_tempData.keys()):
            d_data = d_tempData[s_charName]
            if d_data["retail"] == 0:
                log_sys(f"Warning: Price is 0 for article {s_articleIn} (variant: {s_charName})", 1)
                
            l_varieties.append(self.c_connection.characteristics.get_variety(
                c_charRefIn=d_data["ref"],
                s_charNameIn=s_charName,
                n_priceRetailIn=d_data["retail"],
                n_priceOptIn=d_data["wholesale"],
                d_stocksIn=d_data["stocks"],
                n_pricePurchaseIn=d_data.get("purchase", 0.0)
            ))

        return structures.Nomenclature(
            s_nameIn=s_nameIn,
            s_articleIn=s_articleIn,
            l_varietyIn=l_varieties,
            s_descriptionIn=s_descriptionIn,
            s_unitIn=s_unitIn,
            s_uuidIn=s_uuidIn,
            s_codeIn=s_codeIn
        )

    def get_images(self, c_productObjIn, s_imageDirIn: str = None) -> list:
        """Downloads images associated with a Nomenclature object from 1C to local disk."""
        if not self.c_v8:
            log_sys("Failed to get images: No connection to 1C.", 1)
            return []

        if s_imageDirIn is None:
            s_imageDirIn = "data/images"
        os.makedirs(s_imageDirIn, exist_ok=True)

        l_savedFilenames = []
        l_imageUuids = getattr(c_productObjIn, 'l_images', [])

        if not l_imageUuids:
            try:
                log_sys(f"Falling back to direct image reference query for {c_productObjIn.s_code}...")
                c_uuidObj = self.c_v8.NewObject("UUID", c_productObjIn.s_uuid)
                c_productRef = self.c_v8.Catalogs.Номенклатура.GetRef(c_uuidObj)
                
                c_query = self.c_v8.NewObject("Query")
                c_query.Text = """
                    SELECT Ссылка
                    FROM Справочник.ХранилищеДополнительнойИнформации
                    WHERE Объект = &ProductRef AND ПометкаУдаления = ЛОЖЬ
                """
                c_query.SetParameter("ProductRef", c_productRef)
                c_res = c_query.Execute()
                if not c_res.IsEmpty():
                    c_sel = c_res.Select()
                    while c_sel.Next():
                        l_imageUuids.append(self.c_v8.String(c_sel.Ссылка.UUID()))
            except Exception as e:
                log_sys(f"Error fetching image references for {c_productObjIn.s_code}: {e}", 1)

        # Check local cache and download missing files
        for idx, s_rawUuid in enumerate(l_imageUuids):
            s_cleanUuid = s_rawUuid.replace('{', '').replace('}', '').replace('-', '')
            s_fileName = f"{s_cleanUuid}_{idx}.jpg"
            s_filePath = os.path.join(s_imageDirIn, s_fileName)
            
            if os.path.exists(s_filePath):
                l_savedFilenames.append(s_fileName)
                continue
                
            try:
                log_sys(f"Image {s_fileName} missing locally. Downloading from 1C...")
                c_imgUuidObj = self.c_v8.NewObject("UUID", s_rawUuid)
                c_imgRef = self.c_v8.Catalogs.ХранилищеДополнительнойИнформации.GetRef(c_imgUuidObj)
                
                c_valueStorage = c_imgRef.Хранилище
                c_binaryData = c_valueStorage.Get()
                
                if c_binaryData:
                    c_binaryData.Write(s_filePath)
                    if os.path.exists(s_filePath):
                        l_savedFilenames.append(s_fileName)
                    else:
                        log_sys(f"Failed to write file to disk: {s_filePath}", 1)
                else:
                    log_sys(f"Record for {s_fileName} has empty storage.", 1)
            except Exception as e:
                log_sys(f"Error downloading image {s_fileName}: {e}", 1)

        log_sys(f"Images retrieval completed for {c_productObjIn.s_code}: retrieved {len(l_savedFilenames)} images.")
        return l_savedFilenames

    def get_by_group(self, c_groupRefIn) -> list:
        """Retrieves and processes all Nomenclature items under a given group reference using batching."""
        if not self.c_v8:
            log_sys("Failed to get Nomenclatures: No connection to 1C.", 1)
            return []

        try:
            s_gName = self.c_v8.String(c_groupRefIn)
            log_sys(f"Fetching nomenclature for group: {s_gName} (BATCH MODE)")
            
            c_query = self.c_v8.NewObject("Query")
            c_query.Text = """
                SELECT Ссылка AS Ref,
                       Наименование AS Name,
                       Код AS Code,
                       Артикул AS Article,
                       ЭтоГруппа AS IsFolder,
                       ISNULL(ДополнительноеОписаниеНоменклатуры, "") AS FullDescription,
                       ISNULL(НаименованиеПолное, "") AS FullName,
                       ISNULL(ЕдиницаХраненияОстатков.Наименование, "шт.") AS Unit
                FROM Справочник.Номенклатура
                WHERE Родитель = &GroupRef AND ПометкаУдаления = ЛОЖЬ
            """
            c_query.SetParameter("GroupRef", c_groupRefIn)

            c_result = c_query.Execute()
            if c_result.IsEmpty():
                log_sys(f"No nomenclature items found in group {s_gName}")
                return []

            # 1. Gather basic info
            l_itemsBasicInfo = []
            l_productRefs = []
            
            c_selection = c_result.Select()
            while c_selection.Next():
                if c_selection.IsFolder:
                    continue
                
                c_productRef = c_selection.Ref
                s_productUuid = self.c_v8.String(c_productRef.UUID())
                
                s_description = self.c_v8.String(c_selection.FullDescription)
                if not s_description:
                    s_description = self.c_v8.String(c_selection.FullName)
                
                l_itemsBasicInfo.append({
                    "ref": c_productRef,
                    "uuid": s_productUuid,
                    "name": c_selection.Name,
                    "code": int(self.c_v8.String(c_selection.Code)),
                    "article": c_selection.Article,
                    "description": s_description,
                    "unit": getattr(c_selection, "Unit", "шт.")
                })
                l_productRefs.append(c_productRef)

            if not l_itemsBasicInfo:
                return []

            # 2. Batch fetch details (prices and stocks)
            d_batchDetails = self._fetch_batch_details(l_productRefs)
            
            # 3. Batch fetch characteristics
            l_allCharRefs = []
            for s_productUuid in d_batchDetails:
                for s_charName in d_batchDetails[s_productUuid]:
                    c_charRef = d_batchDetails[s_productUuid][s_charName]["ref"]
                    if c_charRef and not c_charRef.IsEmpty():
                        l_allCharRefs.append(c_charRef)
            
            d_batchChars = self.c_connection.characteristics.fetch_batch(l_allCharRefs)

            # 3.5. Batch fetch image metadata
            d_batchImages = self._fetch_batch_image_metadata(l_productRefs)

            # 4. Construct final nomenclature objects
            l_nomenclatures = []
            for d_item in l_itemsBasicInfo:
                s_productUuid = d_item["uuid"]
                d_productDetails = d_batchDetails.get(s_productUuid, {})
                
                l_varieties = []
                for s_charName in sorted(d_productDetails.keys()):
                    d_data = d_productDetails[s_charName]
                    s_charUuid = self.c_v8.String(d_data["ref"].UUID()) if d_data["ref"] and not d_data["ref"].IsEmpty() else "NULL"
                    
                    l_characteristics = d_batchChars.get(s_charUuid, [])
                    if not l_characteristics:
                        l_characteristics = self.c_connection.characteristics.parse_name(s_charName)

                    l_varieties.append(structures.Variety(
                        n_priceRetailIn=d_data["retail"],
                        n_priceOptIn=d_data["wholesale"],
                        d_countIn=d_data["stocks"],
                        l_characteristicsIn=l_characteristics,
                        n_pricePurchaseIn=d_data.get("purchase", 0.0)
                    ))

                if l_varieties:
                    l_nomenclatures.append(structures.Nomenclature(
                        s_nameIn=d_item["name"],
                        s_articleIn=d_item["article"],
                        l_varietyIn=l_varieties,
                        s_descriptionIn=d_item["description"],
                        s_unitIn=d_item["unit"],
                        s_codeIn=self.c_v8.String(d_item["code"]),
                        l_imagesIn=d_batchImages.get(s_productUuid, [])
                    ))

            log_sys(f"Successfully processed {len(l_nomenclatures)} items in batch mode.")
            return l_nomenclatures

        except Exception as e:
            log_sys(f"Error in getNomenclaturesByGroup (batch): {e}", 1)
            return []
