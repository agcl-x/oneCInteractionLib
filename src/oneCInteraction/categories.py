from .log import log_sys
from . import structures

class CategoriesManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def get(self, s_codeIn: str = "", s_nameIn: str = "") -> structures.Category | None:
        """Finds a single Category by its code or name in the specified catalog."""
        if not self.c_v8:
            log_sys("Failed to get category: No connection to 1C. Returning None", 1)
            return None

        if len(s_codeIn) == 0 and len(s_nameIn) == 0:
            log_sys("Failed to get category: No category code or name. Returning None", 1)
            return None

        try:
            log_sys(f"Trying to get category (code: '{s_codeIn}', name: '{s_nameIn}') from Справочник.ВидыНоменклатуры...")
            c_query = self.c_v8.NewObject("Query")
            
            where_clauses = []
            if s_codeIn:
                where_clauses.append("Код = &Code")
                c_query.SetParameter("Code", s_codeIn)
            if s_nameIn:
                where_clauses.append("Наименование = &Name")
                c_query.SetParameter("Name", s_nameIn)

            c_query.Text = f"""
                SELECT TOP 1 Ссылка AS Ref, 
                       Наименование AS Name,
                       Код AS Code
                FROM Справочник.ВидыНоменклатуры
                WHERE ({" OR ".join(where_clauses)}) AND ПометкаУдаления = ЛОЖЬ
            """

            c_result = c_query.Execute()
            if c_result is None or c_result.IsEmpty():
                log_sys(f"Category (code: '{s_codeIn}', name: '{s_nameIn}') not found. Returning None", 1)
                return None

            c_selection = c_result.Select()
            c_selection.Next()

            s_categoryCode = self.c_v8.String(c_selection.Code)
            s_uuid = self.c_v8.String(c_selection.Ref.UUID())
            log_sys(f"Category '{c_selection.Name}' (code: '{s_categoryCode}') successfully found.")
            return structures.Category(
                s_categoryNameIn=c_selection.Name,
                l_nomenclaturesIn=[],
                c_refIn=c_selection.Ref,
                s_codeIn=s_categoryCode,
                s_uuidIn=s_uuid
            )
        except Exception as e:
            log_sys(f"Error in CategoriesManager.get: {e}", 1)
            return None
