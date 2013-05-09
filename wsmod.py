import platform
if platform.architecture()[0] != "32bit":
    raise Exception("Only 32bit architecture is supported")
import sys

try:
    if sys.hexversion >= 0x02070000 and sys.hexversion < 0x03000000:
        import cefpython_py27 as cefpython
    else:
        raise Exception("Unsupported python version: %s" % sys.version)
except ImportError:
    from cefpython1 import cefpython

import wx
from configobj import ConfigObj

# Which method to use for message loop processing.
#   EVT_IDLE - wx application has priority (default)
#   EVT_TIMER - cef browser has priority
# From the tests it seems that Flash content behaves 
# better when using a timer.
USE_EVT_IDLE = True

def GetApplicationPath(file=None):
    import re, os
    # If file is None return current directory without trailing slash.
    if file is None:
        file = ""
    # Only when relative path.
    if not file.startswith("/") and not file.startswith("\\") and (
            not re.search(r"^[\w-]+:", file)):
        if hasattr(sys, "frozen"):
            path = os.path.dirname(sys.executable)
        elif "__file__" in globals():
            path = os.path.dirname(os.path.realpath(__file__))
        else:
            path = os.getcwd()
        path = path + os.sep + file
        path = re.sub(r"[/\\]+", re.escape(os.sep), path)
        path = re.sub(r"[/\\]+$", "", path)
        return path
    return str(file)

def ExceptHook(type, value, traceObject):
    import traceback, os, time
    # This hook does the following: in case of exception display it,
    # write to error.log, shutdown CEF and exit application.
    error = "\n".join(traceback.format_exception(type, value, traceObject))
    with open(GetApplicationPath("error.log"), "a") as file:
        file.write("\n[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), error))
    print("\n"+error+"\n")
    cefpython.QuitMessageLoop()
    cefpython.Shutdown()
    # So that "finally" does not execute.
    os._exit(1)

class MainFrame(wx.Frame):
    browser = None
    config = None

    def __init__(self):
        # Setup the Chromium Frame
        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY,
                          title='WSMod', size=(375,460))
        self.CreateMenu()

        windowInfo = cefpython.WindowInfo()
        windowInfo.SetAsChild(self.GetHandle())
        self.browser = cefpython.CreateBrowserSync(windowInfo,
                browserSettings={},
                navigateUrl=GetApplicationPath("http://wsmod.com"))

        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        if USE_EVT_IDLE:
            # Bind EVT_IDLE only for the main application frame.
            self.Bind(wx.EVT_IDLE, self.OnIdle)
        
        self.config = ConfigObj("config")

    def CreateMenu(self):

        # Create the Settings Menu
        settings = wx.Menu()
        # Add the Edit Option
        editItem = settings.Append(1, "&Edit"," Information about this program")
        # Bind the Edit Option to self.EditSettings
        self.Bind(wx.EVT_MENU, self.EditSettings, editItem)
        
        # Create the About Menu
        about = wx.Menu()
        # Add it to the About Menu
        menuItem = about.Append(wx.ID_ABOUT, "&WSMod Client"," Information about this program")
        # Bind the About item to self.OnAbout
        self.Bind(wx.EVT_MENU, self.OnAbout, menuItem)

        # Add everything to the menubar
        menubar = wx.MenuBar()
        menubar.Append(settings, "&Settings")
        menubar.Append(about, "&About")

        # Set the menubar on self
        self.SetMenuBar(menubar)
        
    def EditSettings(self, event):
        frame = EditSettings(self)
        frame.Show()
        
    def OnAbout(self, event):
        dlg = wx.MessageDialog( self, 
            "The easiest way to manage your WildStar Addons!", 
            "WSMod.com Client", 
            wx.OK )
        dlg.ShowModal()
        # #
        # config['keyword1'] = 'value1'
        # config['keyword2'] = 'value2'
        # #
        # config['section1'] = {}
        # config['section1']['keyword3'] = 'value3'
        # config['section1']['keyword4'] = 'value4'
        # #
        # section2 = {
        #     'keyword5': 'value5',
        #     'keyword6': 'value6',
        #     'sub-section': {
        #         'keyword7': 'value7'
        #         }
        # }
        # config['section2'] = section2
        # #
        # config['section3'] = {}
        # config['section3']['keyword 8'] = ['value8', 'value9', 'value10']
        # #
        # config.write()

    def OnSetFocus(self, event):
        cefpython.WindowUtils.OnSetFocus(self.GetHandle(), 0, 0, 0)

    def OnSize(self, event):
        cefpython.WindowUtils.OnSize(self.GetHandle(), 0, 0, 0)

    def OnClose(self, event):
        self.browser.CloseBrowser()
        self.Destroy()

    def OnIdle(self, event):
        cefpython.MessageLoopWork()

import re
import unidecode

import shutil
import dulwich.client
from dulwich.repo import Repo
from dulwich import index

class EditSettings(wx.Frame):
    inputs = {}

    def slugify(self, str):
        str = unidecode.unidecode(str).lower()
        return re.sub(r'\W+','-',str)
        
    def __init__(self, wsmod = None):
        wx.Frame.__init__(self, parent=wsmod, id=wx.ID_ANY,
                          title='Settings', size=(420,100))
                          
        self.config = ConfigObj("config")
                          
        # create the main sizer
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        # Add a panel so it looks the correct on all platforms
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.buildInput("Destination")
        self.panel.SetSizer(self.mainSizer)
        save = wx.Button(self.panel, id=wx.ID_ANY, label="Save")
        save.Bind(wx.EVT_BUTTON, self.saveSettings)
        cancel = wx.Button(self.panel, id=wx.ID_ANY, label="Cancel")
        cancel.Bind(wx.EVT_BUTTON, self.onClose)
        change = wx.Button(self.panel, id=wx.ID_ANY, label="Change")
        change.Bind(wx.EVT_BUTTON, self.directorySelect)
        clone = wx.Button(self.panel, id=wx.ID_ANY, label="Clone")
        clone.Bind(wx.EVT_BUTTON, self.testClone)
        update = wx.Button(self.panel, id=wx.ID_ANY, label="Update")
        update.Bind(wx.EVT_BUTTON, self.testUpdate)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(save, 0, wx.ALL, 5)
        sizer.Add(change, 0, wx.ALL, 5)
        sizer.Add(cancel, 0, wx.ALL, 5)
        sizer.Add(clone, 0, wx.ALL, 5)
        self.mainSizer.Add(sizer)
        
    def testUpdate(self, event):
        src = "https://github.com/aaroncox/test.git"
        client, path = dulwich.client.get_transport_and_path(src)
        target = self.config['destination'] + "\\test"
        r = Repo(target)
        remote_refs = client.fetch(src, r)
        r["HEAD"] = remote_refs["HEAD"]
        index.build_index_from_tree(r.path, r.index_path(), r.object_store, r['head'].tree)
        
        for pack in r.object_store.packs:
            pack.close()
        
    def testClone(self, event):
        src = "https://github.com/aaroncox/test.git"
        client, path = dulwich.client.get_transport_and_path(src)
        target = self.config['destination'] + "\\test"

        try:
            shutil.rmtree(target)
        except:
            pass
            
        r = Repo.init(target, mkdir=True)

        remote_refs = client.fetch(src, r)
        r["HEAD"] = remote_refs["HEAD"]
        index.build_index_from_tree(r.path, r.index_path(), r.object_store, r['head'].tree)
        
        for pack in r.object_store.packs:
            pack.close()
            
    def directorySelect(self, event):
        # Args below are: parent, question, dialog title, default answer
        dd = wx.DirDialog(None, "Select directory to open", "~/", 0, (10, 10), wx.Size(400, 300))

        # This function returns the button pressed to close the dialog
        ret = dd.ShowModal()

        # Let's check if user clicked OK or pressed ENTER
        if ret == wx.ID_OK:
            self.inputs['destination'].SetValue(dd.GetPath());
        # 
        # # The dialog is not in the screen anymore, but it's still in memory
        # #for you to access it's values. remove it from there.
        # dd.Destroy()
    #----------------------------------------------------------------------
    def buildInput(self, text):
        """"""
        lblSize = (60,-1)
        slug = self.slugify(text)
        lbl = wx.StaticText(self.panel, label=text, size=lblSize)
        self.inputs[slug] = wx.TextCtrl(self.panel, -1, size=(300, -1))
        if(self.config[slug]):
            self.inputs[slug].SetValue(self.config[slug])

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(lbl, 0, wx.ALL|wx.ALIGN_LEFT, 5)
        sizer.Add(self.inputs[slug], 0, wx.EXPAND, 5)
        self.mainSizer.Add(sizer)
        
    def saveSettings(self, event):
        for k, v in self.inputs.iteritems(): 
            self.config[k] = v.GetValue() 
        self.config.write()
        self.Destroy()
        
    def onClose(self, event):
        """"""
        self.Close()

class MyApp(wx.App):
    timer = None
    timerID = 1

    def OnInit(self):
        if not USE_EVT_IDLE:
            self.CreateTimer()
        frame = MainFrame()
        self.SetTopWindow(frame)
        frame.Show()
        return True

    def CreateTimer(self):
        # See "Making a render loop": 
        # http://wiki.wxwidgets.org/Making_a_render_loop
        # Another approach is to use EVT_IDLE in MainFrame,
        # see which one fits you better.
        self.timer = wx.Timer(self, self.timerID)
        self.timer.Start(10) # 10ms
        wx.EVT_TIMER(self, self.timerID, self.OnTimer)

    def OnTimer(self, event):
        cefpython.SingleMessageLoop()

    def OnExit(self):
        # When app.MainLoop() returns, MessageLoopWork() should 
        # not be called anymore.
        if not USE_EVT_IDLE:
            self.timer.Stop()

if __name__ == '__main__':
    sys.excepthook = ExceptHook
    settings = {
        "log_severity": cefpython.LOGSEVERITY_INFO,
        "log_file": GetApplicationPath("debug.log"),
        "release_dcheck_enabled": True # Enable only when debugging.
    }
    cefpython.Initialize(settings)

    print('wx.version=%s' % wx.version())
    app = MyApp(False)
    app.MainLoop()
    # Let wx.App destructor do the cleanup before calling cefpython.Shutdown().
    del app

    cefpython.Shutdown()
