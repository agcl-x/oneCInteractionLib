from datetime import datetime
from .log import log_sys
from . import structures

class OrdersManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def push(self, c_orderObjIn) -> str:
        """Pushes a new customer order to 1C database, returning the created order number or empty string."""
        if not self.c_v8:
            log_sys("Failed to push order: No connection to 1C. Returning None", 1)
            return None
            
        if not self.c_connection.s_warehouse_code or not self.c_connection.s_counteragent_code or not self.c_connection.s_organisation_code:
            log_sys("Failed to push order: No warehouse code and/or counteragent code and/or organisation code. Returning None", 1)
            return None

        try:
            c_newOrder = self.c_v8.Documents.ЗаказПокупателя.CreateDocument()
            log_sys("Client order was created. Start adding metadata")
            
            # Warehouse
            try:
                log_sys("Trying to get warehouse...")
                c_warehouseRef = self.c_v8.Catalogs.Склады.FindByCode(self.c_connection.s_warehouse_code)
                if c_warehouseRef.IsEmpty():
                    log_sys(f"Can't find main warehouse by code: {self.c_connection.s_warehouse_code}. Returning \"\"", 1)
                c_newOrder.СкладГруппа = c_warehouseRef
            except Exception as e:
                log_sys(f"Failed main warehouse finding: {e}. Returning \"\"", 1)
                return ""

            # Date
            log_sys("Trying to add date to order...")
            c_newOrder.Дата = datetime.now(self.c_connection.tz_kiev).replace(tzinfo=None)
            log_sys("Date successfully added")

            # Client / Counteragent
            try:
                log_sys("Trying to find contragent by code...")
                c_clientRef = self.c_v8.Catalogs.Контрагенты.FindByCode(self.c_connection.s_counteragent_code)
                if c_clientRef.IsEmpty():
                    log_sys(f"Can't find contragent by code: {self.c_connection.s_counteragent_code}. Returning \"\"", 1)
                    return ""

                c_newOrder.Контрагент = c_clientRef
                c_newOrder.ДоговорКонтрагента = c_clientRef.ОсновнойДоговорКонтрагента
                log_sys("Contragent and ContragentContract successfully added to order")
            except Exception as e:
                log_sys(f"Failed contragent finding: {e}. Returning \"\"", 1)
                return ""

            # Organisation
            log_sys("Trying to add organisation to order...")
            c_newOrder.Организация = self.c_v8.Catalogs.Организации.FindByCode(self.c_connection.s_organisation_code)
            if c_newOrder.Организация.IsEmpty():
                log_sys("Failed adding organisation. Returning \"\"", 1)
                return ""
            log_sys("Organisation successfully added to order")

            # Bank Account
            log_sys("Trying to get organisation bank account...")
            c_orgAcc = c_newOrder.Организация.ОсновнойБанковскийСчет
            if not c_orgAcc.IsEmpty():
                log_sys("Bank account successfully got. Trying to add to order...")
                try:
                    c_newOrder.СтруктурнаяЕдиница = c_orgAcc
                    log_sys(f"Bank account successfully added to order: {c_orgAcc.Description}")
                except Exception as e:
                    log_sys(f"Failed adding bank account to order: {e}", 1)
            else:
                log_sys("Failed getting bank account", 1)

            # Currency
            log_sys("Trying to get currency...")
            c_currencyRef = self.c_v8.Catalogs.Валюты.FindByCode("980")
            if c_currencyRef.IsEmpty():
                log_sys("Failed getting currency", 1)
            c_newOrder.ВалютаДокумента = c_currencyRef
            log_sys("Currency successfully added to order")

            # Price Type
            log_sys("Trying to get price type...")
            c_retailPriceRef = self.c_connection.get_price_type_ref("Розничная")
            c_newOrder.ТипЦен = c_retailPriceRef
            log_sys("Price type successfully added to order")

            # Exchange rate settings
            c_newOrder.КурсВзаиморасчетов = 1.0
            c_newOrder.КратностьВзаиморасчетов = 1
            log_sys("КурсВзаиморасчетов, КратностьВзаиморасчетов successfully added to order")

            # Order Items List
            log_sys("Parsing orderItemList")
            for c_item in c_orderObjIn.l_orderItemsList:
                log_sys(f"Trying to get nomenclature({c_item.s_productArticle})")
                c_nomRef = self.c_v8.Catalogs.Номенклатура.FindByAttribute("Артикул", c_item.s_productArticle)

                if c_nomRef.IsEmpty():
                    log_sys("Nomenclature not found, skipping...")
                    continue

                log_sys("Nomenclature successfully fetched")
                s_itemProp = c_item.s_productPropertie
                log_sys(f"Trying to get nomenclature characteristic({s_itemProp})")
                c_charRef = self.c_v8.Catalogs.ХарактеристикиНоменклатуры.EmptyRef()
                if s_itemProp:
                    c_charRef = self.c_v8.Catalogs.ХарактеристикиНоменклатуры.FindByDescription(
                        s_itemProp,
                        True,
                        c_nomRef
                    )
                log_sys("Characteristic successfully fetched")
                
                # Fetch price
                log_sys("Trying to get nomenclature price...")
                try:
                    c_tempNom = self.c_connection.nomenclature.get(s_articleIn=c_item.s_productArticle)
                    n_actualPrice = 0.0
                    if c_tempNom and c_tempNom.l_variety:
                        c_foundVariety = None
                        for c_variety in c_tempNom.l_variety:
                            if not s_itemProp:
                                c_foundVariety = c_variety
                                break
                            
                            for c_char in c_variety.l_characteristics:
                                if c_char.s_value == s_itemProp or f"{c_char.s_name}: {c_char.s_value}" == s_itemProp:
                                    c_foundVariety = c_variety
                                    break
                            if c_foundVariety:
                                break
                        
                        if not c_foundVariety:
                            c_foundVariety = c_tempNom.l_variety[0]
                            
                        n_actualPrice = c_foundVariety.c_priceRetail.n_value
                except Exception as e:
                    log_sys(f"Cannot get nomenclature price: {e}. Setting price to 0", 1)
                    n_actualPrice = 0.0

                log_sys("Creating new orderItem table row. Trying to add new nomenclature...")
                try:
                    c_row = c_newOrder.Товары.Add()
                    c_row.ЕдиницаИзмерения = c_nomRef.ЕдиницаХраненияОстатков
                    c_row.Номенклатура = c_nomRef
                    c_row.ХарактеристикаНоменклатуры = c_charRef
                    c_row.Количество = int(c_item.n_productCount)
                    c_row.Коэффициент = 1
                    c_row.Цена = float(n_actualPrice)
                    c_row.Сумма = float(c_row.Количество * c_row.Цена)
                    log_sys("Nomenclature was successfully added")
                except Exception as e:
                    log_sys(f"Failed adding nomenclature: {e}", 1)
                
            self.update_info(c_orderObjIn)

            try:
                log_sys("Everything done. Trying to post order...")
                c_newOrder.Write(self.c_v8.DocumentWriteMode.Posting)
                log_sys(f"Order was successfully posted. Code: {c_newOrder.Номер}")
                return c_newOrder.Номер
            except Exception as e:
                try:
                    log_sys(f"Failed posting order ({e}). Trying to save it...")
                    c_newOrder.Write(self.c_v8.DocumentWriteMode.Write)
                    log_sys(f"Order was successfully saved. Returning code: {c_newOrder.Номер}")
                    return c_newOrder.Номер
                except Exception as e2:
                    log_sys(f"Failed saving order: {e2}")
                    return ""

        except Exception as e:
            log_sys(f"Unexpected error in posting order: {e}. Returning \"\"", 1)
            return ""

    def get(self, s_codeIn: str):
        """Retrieves and parses a customer order by its 1C document number."""
        if not self.c_v8:
            log_sys("Failed to get order: No connection to 1C. Returning None", 1)
            return None

        if len(s_codeIn) < 2:
            log_sys(f"Failed to get order: Wrong code format ({s_codeIn}). Returning None", 1)
            return None

        try:
            log_sys(f"Searching for order with number: {s_codeIn}...")
            c_orderRef = self.c_v8.Documents.ЗаказПокупателя.FindByNumber(
                s_codeIn, 
                datetime.now(self.c_connection.tz_kiev).replace(tzinfo=None)
            )

            if c_orderRef.IsEmpty():
                log_sys(f"Order with number {s_codeIn} not found in 1C.", 1)
                return None

            log_sys("Order found. Extracting data...")
            c_orderObj1c = c_orderRef.GetObject()

            s_telegramId = c_orderObj1c.Комментарий
            c_customer = structures.Customer(s_customerTelegramIdIn=s_telegramId)
            log_sys(f"Customer Telegram ID extracted from comments: {s_telegramId}")

            l_orderItemsList = []
            for c_row in c_orderObj1c.Товары:
                s_article = c_row.Номенклатура.Артикул
                s_charName = ""
                if not c_row.ХарактеристикаНоменклатуры.IsEmpty():
                    s_charName = c_row.ХарактеристикаНоменклатуры.Наименование

                c_item = structures.OrderItem(
                    s_productArticleIn=s_article,
                    s_productPropertieIn=s_charName,
                    n_productCountIn=c_row.Количество
                )
                l_orderItemsList.append(c_item)

            c_resultOrder = structures.Order(
                c_orderCustomerIn=c_customer,
                l_orderItemsListIn=l_orderItemsList,
                n_orderCodeIn=s_codeIn
            )

            log_sys(f"Order {s_codeIn} successfully fetched and parsed.")
            return c_resultOrder

        except Exception as e:
            log_sys(f"Error occurred while retrieving order {s_codeIn}: {e}", 1)
            return None

    def get_today(self) -> list:
        """Retrieves all orders created today for the configured counteragent bot."""
        if not self.c_v8:
            log_sys("Failed to get today's orders: No connection to 1C.", 1)
            return []

        if len(self.c_connection.s_counteragent_code) < 1:
            log_sys("Failed to get today's orders: No counteragent code. Returning []", 1)
            return []
            
        try:
            log_sys("Fetching today's orders for bot counteragent...")
            c_clientRef = self.c_v8.Catalogs.Контрагенты.FindByCode(self.c_connection.s_counteragent_code)

            if c_clientRef is None or c_clientRef.IsEmpty():
                log_sys(f"Counteragent with code {self.c_connection.s_counteragent_code} not found in 1C.", 1)
                return []

            c_startOfToday = datetime.now(self.c_connection.tz_kiev).replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=None
            )
            c_query = self.c_v8.NewObject("Query")
            c_query.Text = """
                SELECT Номер AS Number
                FROM Документ.ЗаказПокупателя
                WHERE Дата >= &StartDate
                  AND Контрагент = &ClientBot
                  AND ПометкаУдаления = FALSE
                ORDER BY Дата DESC
            """
            c_query.SetParameter("StartDate", c_startOfToday)
            c_query.SetParameter("ClientBot", c_clientRef)

            c_result = c_query.Execute()
            l_ordersList = []

            if not c_result.IsEmpty():
                c_selection = c_result.Select()
                log_sys("Found some orders. Starting to parse...")

                while c_selection.Next():
                    c_orderObj = self.get(c_selection.Number)
                    if c_orderObj:
                        l_ordersList.append(c_orderObj)

            log_sys(f"Successfully retrieved {len(l_ordersList)} orders for today.")
            return l_ordersList

        except Exception as e:
            log_sys(f"Error in getTodayOrders: {e}", 1)
            return []

    def update_info(self, c_orderObjIn) -> bool:
        """Updates the comment details of an order in 1C with PIB, phone, telegram ID, TTN and status."""
        if not self.c_v8:
            log_sys("Failed to update order info: No connection to 1C.", 1)
            return False

        try:
            c_orderRef = self.c_v8.Documents.ЗаказПокупателя.FindByNumber(c_orderObjIn.n_orderCode)

            if c_orderRef.IsEmpty():
                log_sys(f"Order with number {c_orderObjIn.n_orderCode} not found for update.", 1)
                return False

            c_orderObj1c = c_orderRef.GetObject()
            c_customer = c_orderObjIn.c_orderCustomer

            s_pib = c_customer.s_customerPIB
            s_phone = c_customer.s_customerPhone
            s_telegramId = c_customer.s_customerTelegramId
            s_ttn = c_orderObjIn.s_TTN
            s_status = c_orderObjIn.s_status

            s_newComment = f"{s_pib} {s_phone} {s_telegramId} {s_ttn} {s_status}"
            c_orderObj1c.Комментарий = s_newComment
            c_orderObj1c.Write(self.c_v8.DocumentWriteMode.Write)

            log_sys(f"Order {c_orderObjIn.n_orderCode} info successfully updated in 1C.")
            return True

        except Exception as e:
            log_sys(f"Error occurred while updating order {c_orderObjIn.n_orderCode}: {e}", 1)
            return False
