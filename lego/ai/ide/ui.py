from fasthtml.common import *
from monsterui.franken import *

editor_script = Script("""

""")

def Toolbar():
    return Div(
        Select(
            Option("JavaScript", value="javascript"),Option("Python", value="python"),
            Option("HTML", value="html"),Option("CSS", value="css"),
        id="language",cls="mr-2 p-2 border rounded"),
        Button("Run", id="run", cls=ButtonT.primary),
        Button("Save", id="save", cls=ButtonT.secondary), cls="bg-card flex items-center w-full")

def CodeEditor():
    return (
        Div(Toolbar(),
            Div(Div(id="editor", cls="w-full h-full"),
                Script("me().on('contextmenu', ev => { halt(ev); me('#context-menu').send('show', {x: ev.pageX, y: ev.pageY})})"),
                cls="flex-grow w-full"
                ),
            cls="flex flex-col h-screen w-full"
            ),
        editor_script
        )