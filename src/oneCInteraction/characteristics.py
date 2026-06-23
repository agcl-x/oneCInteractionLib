from .log import log_sys
from . import structures

class CharacteristicsManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    @staticmethod
    def parse_name(s_charNameIn: str) -> list:
        """Parses a characteristic name string into a list of Characteristic objects."""
        if not s_charNameIn or s_charNameIn in ["NULL", "Без характеристики"]:
            return []
            
        if " - " in s_charNameIn:
            l_parts = s_charNameIn.split(" - ")
            s_value = l_parts[1] if len(l_parts) > 1 else l_parts[0]
            return [structures.Characteristic("Характеристика", s_value)]
        elif ":" in s_charNameIn:
            l_parts = s_charNameIn.split(":")
            s_name = l_parts[0].strip()
            s_value = l_parts[1].strip() if len(l_parts) > 1 else ""
            return [structures.Characteristic(s_name, s_value)]
        else:
            return [structures.Characteristic("Характеристика", s_charNameIn)]

    def get(self, c_charRefIn, s_charNameIn: str = "") -> list:
        """Fetches characteristic properties from registry or parses description."""
        l_characteristics = []
        if c_charRefIn is not None and not c_charRefIn.IsEmpty():
            try:
                c_query = self.c_v8.NewObject("Query")
                c_query.Text = """
                    SELECT
                        Properties.Свойство.Наименование AS PropName,
                        Properties.Значение.Наименование AS ValName
                    FROM
                        РегистрСведений.ЗначенияСвойствОбъектов AS Properties
                    WHERE
                        Properties.Объект = &CharRef
                """
                c_query.SetParameter("CharRef", c_charRefIn)
                c_res = c_query.Execute()
                if c_res is not None and not c_res.IsEmpty():
                    c_sel = c_res.Select()
                    while c_sel.Next():
                        l_characteristics.append(structures.Characteristic(c_sel.PropName, c_sel.ValName))
            except Exception as e:
                log_sys(f"Error fetching characteristics for {s_charNameIn}: {e}", 1)
        
        # Fallback to string parsing if properties were not found in registry
        if not l_characteristics:
            l_characteristics = self.parse_name(s_charNameIn)
        
        return l_characteristics

    def get_variety(self, c_charRefIn, s_charNameIn: str, n_priceIn: float, n_priceOptIn: float, d_stocksIn: dict):
        """Creates a Variety object with its characteristics and stock counts."""
        l_characteristics = self.get(c_charRefIn, s_charNameIn)
        return structures.Variety(
            n_priceIn=n_priceIn,
            n_priceOptIn=n_priceOptIn,
            d_countIn=d_stocksIn,
            l_characteristicsIn=l_characteristics
        )

    def fetch_batch(self, l_charRefsIn: list) -> dict:
        """Batch fetches properties and values for a list of characteristics."""
        if not self.c_v8 or not l_charRefsIn:
            return {}

        log_sys(f"Batch fetching properties for {len(l_charRefsIn)} characteristics...")
        
        c_charRefsV8 = self.c_v8.NewObject("ValueList")
        for c_ref in l_charRefsIn:
            if c_ref and not c_ref.IsEmpty():
                c_charRefsV8.Add(c_ref)

        d_charProps = {} # {char_uuid: [Characteristic]}

        if c_charRefsV8.Count() > 0:
            try:
                c_propQuery = self.c_v8.NewObject("Query")
                c_propQuery.Text = """
                    SELECT
                        Properties.Объект AS CharRef,
                        Properties.Свойство.Наименование AS PropName,
                        Properties.Значение.Наименование AS ValName
                    FROM
                        РегистрСведений.ЗначенияСвойствОбъектов AS Properties
                    WHERE
                        Properties.Объект В (&CharRefs)
                """
                c_propQuery.SetParameter("CharRefs", c_charRefsV8)
                c_propRes = c_propQuery.Execute()
                if c_propRes is not None and not c_propRes.IsEmpty():
                    c_sel = c_propRes.Select()
                    while c_sel.Next():
                        s_uuid = self.c_v8.String(c_sel.CharRef.UUID())
                        if s_uuid not in d_charProps:
                            d_charProps[s_uuid] = []
                        d_charProps[s_uuid].append(structures.Characteristic(c_sel.PropName, c_sel.ValName))
            except Exception as e:
                log_sys(f"Error batch fetching characteristics: {e}", 1)

        return d_charProps
