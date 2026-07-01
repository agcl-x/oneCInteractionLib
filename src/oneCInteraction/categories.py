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
            log_sys(f"Trying to get category (code: '{s_codeIn}', name: '{s_nameIn}') from Справочник.КатегорииОбъектов...")
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
                FROM Справочник.КатегорииОбъектов
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

    def create(self, s_nameIn: str) -> structures.Category | None:
        """Creates a new Category in Справочник.КатегорииОбъектов."""
        if not self.c_v8:
            log_sys("Failed to create category: No connection to 1C. Returning None", 1)
            return None

        if len(s_nameIn) == 0:
            log_sys("Failed to create category: Name is empty. Returning None", 1)
            return None

        try:
            # Determine the maximum description length from 1C metadata with default fallbacks
            n_maxLength = 100  # Default fallback
            try:
                n_maxLength = int(self.c_v8.Metadata.Catalogs.КатегорииОбъектов.DescriptionLength)
            except Exception:
                try:
                    n_maxLength = int(self.c_v8.Метаданные.Справочники.КатегорииОбъектов.ДлинаНаименования)
                except Exception:
                    pass

            if len(s_nameIn) > n_maxLength:
                log_sys(f"Warning: Category name '{s_nameIn}' exceeds maximum allowed length of {n_maxLength} characters. Truncating.", 1)
                s_nameIn = s_nameIn[:n_maxLength]

            log_sys(f"Creating new category '{s_nameIn}' in Справочник.КатегорииОбъектов...")
            
            c_newCategory = self.c_v8.Catalogs.КатегорииОбъектов.CreateItem()
            c_newCategory.Наименование = s_nameIn
            c_newCategory.Write()
            
            s_categoryCode = self.c_v8.String(c_newCategory.Код)
            s_uuid = self.c_v8.String(c_newCategory.Ссылка.UUID())
            
            log_sys(f"Category '{s_nameIn}' (code: '{s_categoryCode}') successfully created.")
            return structures.Category(
                s_categoryNameIn=s_nameIn,
                l_nomenclaturesIn=[],
                c_refIn=c_newCategory.Ссылка,
                s_codeIn=s_categoryCode,
                s_uuidIn=s_uuid
            )
        except Exception as e:
            log_sys(f"Error in CategoriesManager.create: {e}", 1)
            return None

