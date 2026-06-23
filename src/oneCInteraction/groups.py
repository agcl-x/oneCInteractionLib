from .log import log_sys
from . import structures

class GroupsManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def get_tree(self, sl_ignoredCategoriesNamesIn: list) -> list:
        """Retrieves and builds hierarchical group structure excluding ignored names."""
        if not self.c_v8:
            log_sys("Failed to get hierarchical groups: No connection to 1C.", 1)
            return []

        try:
            c_ignoredVl = self.c_v8.NewObject("ValueList")
            
            if sl_ignoredCategoriesNamesIn:
                log_sys(f"Finding references for ignored categories: {sl_ignoredCategoriesNamesIn}")
                c_refQuery = self.c_v8.NewObject("Query")

                l_whereClauses = []
                for i in range(len(sl_ignoredCategoriesNamesIn)):
                    l_whereClauses.append(f"Наименование = &Name{i}")
                
                c_refQuery.Text = f"SELECT Ссылка FROM Справочник.Номенклатура WHERE ({' OR '.join(l_whereClauses)}) AND ЭтоГруппа = ИСТИНА"
                
                for i, s_name in enumerate(sl_ignoredCategoriesNamesIn):
                    c_refQuery.SetParameter(f"Name{i}", s_name)
                    
                c_refRes = c_refQuery.Execute()
                if not c_refRes.IsEmpty():
                    c_sel = c_refRes.Select()
                    while c_sel.Next():
                        c_ignoredVl.Add(c_sel.Ссылка)

            log_sys("Fetching nomenclature groups (excluding ignored branches)...")
            c_query = self.c_v8.NewObject("Query")
            s_queryText = """
                SELECT Ссылка AS Ref, 
                       Наименование AS Name, 
                       Код AS Code,
                       Родитель AS Parent
                FROM Справочник.Номенклатура
                WHERE ЭтоГруппа = ИСТИНА AND ПометкаУдаления = ЛОЖЬ
            """
            
            if c_ignoredVl.Count() > 0:
                s_queryText += " AND NOT Ссылка В ИЕРАРХИИ(&IgnoredRefs)"
                c_query.SetParameter("IgnoredRefs", c_ignoredVl)
            
            s_queryText += " ORDER BY Родитель, Наименование"
            c_query.Text = s_queryText
            
            c_result = c_query.Execute()

            d_groupsDict = {}
            l_rootGroups = []

            if not c_result.IsEmpty():
                c_selection = c_result.Select()
                while c_selection.Next():
                    c_groupRef = c_selection.Ref
                    s_groupName = c_selection.Name
                    s_groupCode = self.c_v8.String(c_selection.Code)
                    c_parentRef = c_selection.Parent

                    s_refKey = self.c_v8.String(c_groupRef.UUID())
                    c_groupObj = structures.Group(
                        s_groupNameIn=s_groupName, 
                        l_nomenclaturesIn=[], 
                        c_refIn=c_groupRef, 
                        s_codeIn=s_groupCode,
                        s_uuidIn=s_refKey
                    )
                    
                    s_parentKey = self.c_v8.String(c_parentRef.UUID()) if not c_parentRef.IsEmpty() else None

                    d_groupsDict[s_refKey] = {
                        'obj': c_groupObj,
                        'parent': s_parentKey
                    }

                for s_ref, d_data in d_groupsDict.items():
                    s_parentKey = d_data['parent']
                    if s_parentKey and s_parentKey in d_groupsDict:
                        d_groupsDict[s_parentKey]['obj'].l_subGroups.append(d_data['obj'])
                    else:
                        l_rootGroups.append(d_data['obj'])

            log_sys(f"Successfully fetched and organized {len(d_groupsDict)} groups.")
            return l_rootGroups

        except Exception as e:
            log_sys(f"Error in getHierarchicalGroups: {e}", 1)
            return []

    def get_by_name(self, s_nameIn: str):
        """Finds a single category Group by its name."""
        if not self.c_v8:
            log_sys("Failed to get category: No connection to 1C. Returning None", 1)
            return None

        try:
            log_sys(f"Trying to get category by name: {s_nameIn}...")
            c_query = self.c_v8.NewObject("Query")
            c_query.Text = """
                SELECT TOP 1 Ссылка AS Ref, 
                       Наименование AS Name,
                       Код AS Code
                FROM Справочник.Номенклатура
                WHERE Наименование = &Name AND ЭтоГруппа = ИСТИНА AND ПометкаУдаления = ЛОЖЬ
            """
            c_query.SetParameter("Name", s_nameIn)

            c_result = c_query.Execute()
            if c_result.IsEmpty():
                log_sys(f"Category '{s_nameIn}' not found. Returning None", 1)
                return None

            c_selection = c_result.Select()
            c_selection.Next()

            s_groupCode = self.c_v8.String(c_selection.Code)
            log_sys(f"Category '{s_nameIn}' successfully found.")
            return structures.Group(s_groupNameIn=c_selection.Name, l_nomenclaturesIn=[], c_refIn=c_selection.Ref, s_codeIn=s_groupCode)
        except Exception as e:
            log_sys(f"Error in getCategoryByName: {e}", 1)
            return None

    def get_full_path(self, c_groupRefIn) -> str:
        """Returns the full hierarchical path of the group (e.g. 'Parent > Subgroup')."""
        if c_groupRefIn is None or c_groupRefIn.IsEmpty():
            return ""
        
        l_pathParts = []
        c_currentRef = c_groupRefIn
        
        try:
            while c_currentRef is not None and not c_currentRef.IsEmpty():
                c_groupObj = c_currentRef.GetObject()
                l_pathParts.insert(0, c_groupObj.Наименование)
                c_currentRef = c_groupObj.Родитель
            
            s_fullPath = " > ".join(l_pathParts)
            log_sys(f"Full group path built: '{s_fullPath}'")
            return s_fullPath
        except Exception as e:
            log_sys(f"Error in getFullGroupPath: {e}", 1)
            return ""
