import gtk

def createMenu(delegate, menu_file):
    window=delegate.get_toplevel()

    uimanager = gtk.UIManager()
    # Create a ToggleAction, etc.

    actiongroup = gtk.ActionGroup('UIManagerExample')
    delegate.actiongroup = actiongroup

    actiongroup.add_toggle_actions([('Mute', None, '_Mute', '<Control>m',
                                         'Mute the volume', delegate.mute_cb)])

    # Create actions
    actiongroup.add_actions([
            ('Quit', gtk.STOCK_QUIT, '_Quit me!', None,
             'Quit the Program', delegate.destroy),
            ('File', None, '_File'),
            ('Edit', None, '_Edit'),
            ('Source', None, '_Source'),
            ('Plot', None, '_Plot')
            ])

    actiongroup.get_action('Quit').set_property('short-label', '_Quit')

    actiongroup.add_actions([
            ('Open', gtk.STOCK_OPEN, 'Open Session...', '<Control>o', "Open a session from disk", delegate.load_cb),
            ('Save', gtk.STOCK_SAVE, 'Save Session...', '<Control>s', "Save the session to disk", delegate.save_cb),
            ('Save As', gtk.STOCK_SAVE_AS, 'Save Session As...', '<Shift><Control>s', "Save the session to disk under a new name", delegate.save_as_cb)
            ])

    # Edit actions
    actiongroup.add_actions([
            ('Copy',None,'Copy', None,"Copy top clipboard",delegate.copy_cb),
            ('Cut',None,'Cut', None,"Cut to clipboard",delegate.cut_cb),
            ('Paste',None,'Paste', None,"Paste from the clipboard",delegate.paste_cb)
            ])

    # Create some source Actions
    actiongroup.add_actions([
            ('Add Source', None, '_Add Source', None,
             'Add an empty source.', delegate.add_source_cb),
            ('Add Source from File', None, '_Add Source from File', '<Shift><Control>f',
             'Add a source with data from a textfile.', delegate.add_source_from_file_cb),

            ('Add Source from Clipboard', None, '_Add Source from Clipboard', '<Shift><Control>a',
             'Add a source with data from the clipboard contents.', delegate.add_source_from_clipboard_cb),
            ('Duplicate Source', None, '_Duplicate Source', '<Control>d',
             'Duplicate the selected source(s).', delegate.dup_source_cb),
            ('Remove Source', None, '_Remove Source', 'Delete',
             'Remove selected source(s) from the list.', delegate.rem_source_cb),
            ('Add Folder', None, 'Add _Folder', '<Control>f',
             'Add a folder.', delegate.add_folder_cb),
            ('Export to file', None, '_Export to file', '<Control>e',
             'Save selected Source data to file.', delegate.export_source_cb),
            ])
    #Plot actions
    actiongroup.add_actions([
            ('New Plot', None, 'New _Plot', '<Control>p',
             'Create a new plot with selected source(s).',
             delegate.new_plot_cb),
            ('Delete Plot', None, 'Delete Plot', '<Control>Delete',
             'Delete the current plot.', delegate.del_plot_cb),
            ('Select Sources', None, 'Select Sources', None,
             'Select all Sources present in the current Plot.',
             delegate.select_plot_sources)
            ])


    uimanager.insert_action_group(actiongroup, 0)

    accelgroup = uimanager.get_accel_group()
    window.add_accel_group(accelgroup)
    merge_id = uimanager.add_ui_from_file(menu_file)

    menubar = uimanager.get_widget('/MenuBar')
    #toolbar = uimanager.get_widget('/Toolbar')

    delegate.menubox.pack_start(menubar, expand=True)
    #self.vbox1.pack_start(toolbar, False)

    return menubar, uimanager
