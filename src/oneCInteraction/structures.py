from datetime import datetime

class Nomenclature:
    def __init__(
        self,
        s_nameIn: str,
        s_articleIn: str,
        l_varietyIn: list,
        s_descriptionIn: str = "",
        s_unitIn: str = "шт.",
        s_parent_uuidIn: str = "",
        s_uuidIn: str = "",
        s_codeIn: str = "",
        l_imagesIn: list = None
    ):
        self.s_name = s_nameIn
        self.s_article = s_articleIn
        self.s_description = s_descriptionIn
        self.l_variety = l_varietyIn
        self.s_unit = s_unitIn
        self.s_parent_uuid = s_parent_uuidIn
        self.s_uuid = s_uuidIn
        self.s_code = s_codeIn
        self.l_images = l_imagesIn if l_imagesIn is not None else []

class Variety:
    def __init__(
        self,
        n_priceRetailIn: float,
        n_priceOptIn: float,
        d_countIn: dict,
        l_characteristicsIn: list,
        n_pricePurchaseIn: float = 0.0
    ):
        self.n_priceRetail = n_priceRetailIn
        self.n_priceOpt = n_priceOptIn
        self.n_pricePurchase = n_pricePurchaseIn
        self.d_count = d_countIn
        self.l_characteristics = l_characteristicsIn

class Characteristic:
    def __init__(self, s_nameIn: str, s_valueIn: str):
        self.s_name = s_nameIn
        self.s_value = s_valueIn

class Group:
    def __init__(
        self,
        s_groupNameIn: str,
        l_nomenclaturesIn: list = None,
        l_subGroupsIn: list = None,
        c_refIn = None,
        s_codeIn: str = None,
        s_uuidIn: str = None
    ):
        self.s_name = s_groupNameIn
        self.l_subGroups = l_subGroupsIn if l_subGroupsIn is not None else []
        self.l_nomenclatures = l_nomenclaturesIn if l_nomenclaturesIn is not None else []
        self.c_ref = c_refIn
        self.s_code = s_codeIn
        self.s_uuid = s_uuidIn

class Customer:
    def __init__(
        self,
        s_customerTelegramIdIn: str,
        s_customerPIBIn: str = "",
        s_customerPhoneIn: str = "",
        s_customerAddressIn: str = ""
    ):
        self.s_customerTelegramId = s_customerTelegramIdIn
        self.s_customerPIB = s_customerPIBIn
        self.s_customerPhone = s_customerPhoneIn
        self.s_customerAddress = s_customerAddressIn

class OrderItem:
    def __init__(
        self,
        s_productArticleIn: str,
        s_productPropertieIn: str = "",
        n_productCountIn: int = 1
    ):
        self.s_productArticle = s_productArticleIn
        self.s_productPropertie = s_productPropertieIn
        self.n_productCount = n_productCountIn

    def __dict__(self):
        return {f'{self.s_productArticle}': self.s_productPropertie}

class Order:
    def __init__(
        self,
        c_orderCustomerIn: Customer = None,
        l_orderItemsListIn: list = None,
        n_orderCodeIn: int = 0
    ):
        self.c_orderCustomer = c_orderCustomerIn
        self.l_orderItemsList = l_orderItemsListIn if l_orderItemsListIn is not None else []
        self.s_TTN = ""
        self.s_status = ""
        self.s_date = datetime.now().strftime("%H:%M %d.%m.%Y")
        self.n_orderCode = n_orderCodeIn

    def __str__(self):
        s_outString = f'''\t<b>ЗАМОВЛЕННЯ №{self.n_orderCode}</b>
        📅Дата: {self.s_date}\n
        🔗Користувач: <a href="tg://user?id={self.c_orderCustomer.s_customerTelegramId}">Замовник</a>
            🙎‍♂️ПІБ: {self.c_orderCustomer.s_customerPIB}
            📞Номер телефону: {self.c_orderCustomer.s_customerPhone}
            🏠Адреса: {self.c_orderCustomer.s_customerAddress}\n
        🔢ТТН: {self.s_TTN}
        📩Статус: {self.s_status}\n
        📃Список покупок:\n'''
        for c_item in self.l_orderItemsList:
            s_outString += f'\t\t⚫{c_item.s_productArticle}:{c_item.s_productPropertie} - {c_item.n_productCount}\n'

        return s_outString
