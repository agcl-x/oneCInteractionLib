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

class Price:
    def __init__(self, n_value: float, dt_assigned: datetime = None, s_type: str = ""):
        self.n_value = float(n_value)
        self.dt_assigned = dt_assigned  # datetime object
        self.s_type = s_type            # Russian name, e.g. "Розничная", "Оптовая", "Закупочная"

    def __repr__(self):
        s_date = self.dt_assigned.strftime("%d.%m.%Y") if self.dt_assigned else "None"
        return f"Price({self.n_value}, date={s_date}, type='{self.s_type}')"

class Variety:
    def __init__(
        self,
        c_priceRetailIn: Price,
        c_priceOptIn: Price,
        d_countIn: dict,
        l_characteristicsIn: list,
        c_pricePurchaseIn: Price = None
    ):
        self.c_priceRetail = c_priceRetailIn
        self.c_priceOpt = c_priceOptIn
        self.c_pricePurchase = c_pricePurchaseIn if c_pricePurchaseIn is not None else Price(0.0, s_type="Закупочная")
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

class Category:
    def __init__(
        self,
        s_categoryNameIn: str,
        l_nomenclaturesIn: list = None,
        c_refIn = None,
        s_codeIn: str = None,
        s_uuidIn: str = None
    ):
        self.s_name = s_categoryNameIn
        self.l_nomenclatures = l_nomenclaturesIn if l_nomenclaturesIn is not None else []
        self.c_ref = c_refIn
        self.s_code = s_codeIn
        self.s_uuid = s_uuidIn

class Customer:
    def __init__(
        self,
        s_customerIdIn: str,
        s_customerNameIn: str = "",
        s_customerSurnameIn: str = "",
        s_customerPatronymicIn: str = "",
        s_customerPhoneIn: str = "",
        s_customerAddressIn: str = "",
        s_customerCodeIn: str = ""
    ):
        self.s_customerId = s_customerIdIn
        self.s_customerName = s_customerNameIn
        self.s_customerSurname = s_customerSurnameIn
        self.s_customerPatronymic = s_customerPatronymicIn
        self.s_customerPhone = s_customerPhoneIn
        self.s_customerAddress = s_customerAddressIn
        self.s_customerCode = s_customerCodeIn

class OrderItem:
    def __init__(
        self,
        s_productCodeIn: str,
        c_varietyIn: Variety = None,
        n_productCountIn: int = 1
    ):
        self.s_productCode = s_productCodeIn
        self.c_variety = c_varietyIn
        self.n_productCount = n_productCountIn


class Order:
    def __init__(
        self,
        c_orderCustomerIn: Customer = None,
        l_orderItemsListIn: list = None,
        n_orderCodeIn: int = 0,
        s_price_typeIn: str = "",
        s_commentIn: str = ""
    ):
        self.c_orderCustomer = c_orderCustomerIn
        self.l_orderItemsList = l_orderItemsListIn if l_orderItemsListIn is not None else []
        self.s_TTN = ""
        self.s_status = ""
        self.s_date = datetime.now().strftime("%H:%M %d.%m.%Y")
        self.n_orderCode = n_orderCodeIn
        self.s_price_type = s_price_typeIn
        self.s_comment = s_commentIn


class DiscountGroup:
    def __init__(
        self,
        s_nameIn: str,
        s_document_numberIn: str,
        s_discount_type_codeIn: str,
        n_discount_percentIn: float,
        l_nomenclaturesIn: list
    ):
        self.s_name = s_nameIn
        self.s_document_number = s_document_numberIn
        self.s_discount_type_code = s_discount_type_codeIn
        self.n_discount_percent = float(n_discount_percentIn)
        self.l_nomenclatures = l_nomenclaturesIn

