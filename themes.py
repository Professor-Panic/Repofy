from textual.theme import Theme
import json
test={"name":"tokyo-night"}
def SaveTheme(theme_data):
    with open("themes.json","w")as f:
        json.dump(theme_data,f)
def LoadTheme():
    loaded_data=""
    with open('themes.json', 'r') as file:
        loaded_data = json.load(file)
    return loaded_data