#!/usr/bin/env python

import gtk
#from gtk import gdk
import os
import shelve
#import pickle
#import time
#import copy

from gtk import RESPONSE_YES

#from kiwi.ui import gadgets
from kiwi.ui.delegates import Delegate
#from kiwi.model import Model
from kiwi.ui.objectlist import ObjectList, Column
import kiwi.ui.dialogs as dialogs
from kiwi import ValueUnset
from kiwi.enums import ComboColumn, ComboMode

from urllib import unquote
#import operator

from numpy import transpose, savetxt, array, arange


from fileutils import load_data
from menu import createMenu
from plot import Line, Plot
from source import Source, Folder, SourceError, GeneratedColumn
#from browse import file_browse

def format_test(hej):
    return hej

FILE_EXT="plh"

class PlotHole(Delegate):

    src_columns=[
        Column("toggle", title="P", data_type=bool, radio=False,\
                   editable=True),
        Column("id", title="#", sorted=True),   #, column="toggle"),
        Column("name", use_markup=True, format_func=format_test,\
                   searchable=True, editable=True),
        Column("file")
        ]

    lines_columns=[
        Column("source.id", title="S", data_type=int),
        Column("x_column", title="X"),
        Column("y_column", title="Y"),
        Column("label", editable=True)
        ]

    gen_columns=[
        Column("enabled", data_type=bool, editable=True, radio=False),
        Column("id", column="enabled"),
        Column("name", editable=True),
        Column("expr", editable=True, expand=True)
        ]

    gladefile="plothole_kiwi"
    session_file=None
    src_id=plt_id=0

    def __init__(self):
        Delegate.__init__(self, delete_handler=self.quit_if_last)

        #Add a menu in a non-kiwi way, because I can't get gazpacho to do it!
        self.menubar, self.uimanager = createMenu(self, "plothole_ui.xml")
        merge_id = self.uimanager.new_merge_id()
        #self.uimanager.add_ui(merge_id, "/MenuBar/Plot/", "test", "New Plot", gtk.UI_MANAGER_MENUITEM, False)
        self.plotmenu = self.uimanager.get_widget("/MenuBar/Plot").get_submenu()
        testitem = gtk.MenuItem(None)
        self.plotmenu.append(testitem)
        #testitem.connect("activate", self.new_plot_cb)
        testitem.show()

        #Setup the Source view
        self.source_list.set_columns(self.src_columns)
        self.source_list.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.source_listview=self.source_list.get_treeview()
        name_col=self.source_list.get_treeview_column(self.src_columns[2])
        self.source_listview.search_column=2

        #Setup the Lines list
        self.lines_list.set_headers_visible(True)
        self.lines_list.set_columns(self.lines_columns)

        self.gen_col_list.set_headers_visible(False)
        self.gen_col_list.set_columns(self.gen_columns)

        self.name.set_property('data-type', str)
        self.x_col.set_property('data-type', int)
        self.y_col.set_property('data-type', int)


        self.x_expr.set_property('data-type', str)
        self.y_expr.set_property('data-type', str)
        self.title.set_property('data-type', str)
        self.label.set_property('data-type', str)
        self.style.set_property('data-type', str)
        self.marker.set_property('data-type', str)
        self.legend_loc.set_property('data-type', str)
        self.legend_size.set_property('data-type', str)
        self.x_axis_label.set_property('data-type', str)
        self.y_axis_label.set_property('data-type', str)

        self.context_id = self.statusbar.get_context_id("test")

        self.plot_model=self.plt_combo.get_model()

        #Access to global clipboard
        self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        self.clipboard_text=""

        self.loading=False  #Are we currently loading a saved session?
                            #Ugly hack to avoid some recursion problems.
        self.color_button=gtk.ColorButton()

        #Source clipboard
        self.src_clipboard=[]
        self.src_clipboard_cut=False

        self.style.prefill([("-","-"), ("--","--"), (":", ":"), ("-.","-."), ("_-", "steps"), (" ","None")])
        self.marker.prefill([(".", "."), ("o", "o"), ("^", "^"), ("v", "v"), ("+", "+"), ("x", "x"), ("s", "s"), (",",","), (" ", "None")])

        #x_col_liststore = self.x_col.get_model_items()
        #x_col_liststore.set_column_types("str", "str")
        self.x_col.prefill([("0",0),("1",1)])
        self.y_col.prefill([("0",0),("1",1)])


        self.legend_loc.prefill(["best", "upper right", "center right",
                                 "lower right", "lower center", "lower left",
                                 "center left", "upper left", "upper center",
                                 "center"])

        self.legend_size.prefill(["xx-small", "x-small", "small",
                                  "medium", "large", "x-large", "xx-large"])

        self.src_proxy=self.add_proxy(Source(), [
                "name", "x_expr_enable", "x_expr", "x_col", "y_col",
                "y_expr_enable", "y_expr", "norm_enable", "norm_min_pt",
                "norm_min_y", "norm_max_pt", "norm_max_y", "comment",
                "transpose"
                ])
        self.plt_proxy=self.add_proxy(Plot(), [
                "title", "shown", "xlim_enable", "ylim_enable",
                "xlim_min", "xlim_max", "ylim_min", "ylim_max",
                "legend_enable", "legend_loc", "legend_size", "legend_border",
                "x_axis_label", "x_axis_label_enable",
                "y_axis_label", "y_axis_label_enable",
                "x_grid_enable", "y_grid_enable",
                "x_majorticks_enable", "x_minorticks_enable",
                "x_majorticks_maxn", "x_minorticks_maxn",
                "y_majorticks_enable", "y_minorticks_enable",
                "y_majorticks_maxn", "y_minorticks_maxn",
                "mpl_commands", "figheight", "figwidth",
                "x_log_enable", "y_log_enable",
                ])

        self.line_proxy=self.add_proxy(Line(), [
                "label", "style", "marker", "width", "x_scale_enable",
                "y_scale_enable", "x_scale", "y_scale",
                "x_shift_enable", "y_shift_enable", "x_shift", "y_shift",
                "x_column", "y_column", "source_columns_enable"
                ])

    #        self.gen_col_proxy=self.add_proxy(GeneratedColumn(), [
    #                "id", "name", "expr"
    #                ])

        #Setup the line color selector (is there a more "kiwi" way?)
        self.line_colorseldlg = None
        self.color = self.line_color_area.get_colormap().alloc_color(0, 65535, 0)
        self.line_color_area.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.line_color_area.connect("event",  self.line_color_area_event)


        #These are "hooks", which get called every time a proxy is updated.
        self.src_proxy.proxy_updated = self.src_proxy_updated
        self.plt_proxy.proxy_updated = self.plt_proxy_updated
        self.line_proxy.proxy_updated = self.line_proxy_updated

        #Drag'n drop Sources setup
        source_listview = self.source_list.get_treeview()
        source_listview.enable_model_drag_dest([("text/uri-list",0,80)], gtk.gdk.ACTION_COPY)
        self.source_list.enable_dnd()
        source_listview.connect("drag_data_received",self.on_drag_data_received)

        #Initial widget sensitivity
        self.expressions_expander.set_sensitive(False)
        self.source_pane.set_sensitive(False)
        self.plot_pane.set_sensitive(False)
        self.line_notebook.set_sensitive(False)

        #experimenting with setting up a filter for the source list
        #self.src_filter=self.source_list.get_model().filter_new(root=None)
        #self.src_filter.set_visible_func(self.src_filter_func, data=None)

    #Non-functional source filter. This would be useful.
    def src_filter_func(self, model, iter, data):
        src = model.get(iter, 0)[0]
        if not src is None:
            print "filt:", src.name
            #return src.name.startswith("B")
            return True
        else:
            return False

    def clipboard_text_received(self, clipboard, text, data):
        self.clipboard_text=text
        return

    def round_to_n(self,x,n):
        """Rounds x to n significant digits"""
        if n < 1:
            raise ValueError("number of significant digits must be >= 1")
        return float("%.*e" % (n-1, x))


    #Hooks that run when a value looked after by a proxy is changed

    def src_proxy_updated(self,widget,attribute,value):
      """Hook that runs every time a Source is changed"""
      print self.loading
      if not self.loading:
        sel_source_old=self.source_list.get_selected_rows()[0]
        self.source_list.update(self.src_proxy._get_model())
        sel_sources=self.source_list.get_selected_rows()
        sel_source=sel_sources[0]
        if sel_source_old!=sel_source:
            self.statusbar.pop(self.context_id)
            self.statusbar.push(self.context_id, "Source "+str(sel_source.id)+": '"+sel_source.name+"', ("+str(len(sel_source.data))+" cols, "+str(len(sel_source.data[0]))+" pts)")

        #plots_to_update = set([])

        for source in sel_sources:

            if attribute in ["x_col"]:
                if not self.loading:
                    source.x_col = min(value, len(source.data)-1)
                    source.update_x_data(self.source_list[:])
                    #print "x_col:", source.x_col
                    source.notify()

            elif attribute in ["y_col"]:
                if not self.loading:
                    source.y_col = min(value, len(source.data)-1)
                    source.update_y_data(self.source_list[:])
                    #print "y_col:", source.y_col
                    source.notify()

            elif attribute in ["x_expr"]:
                setattr(source,attribute,getattr(self,attribute).read())
                if not source.update_x_data(self.source_list[:]):
                    self.x_expr_enable.update(False)
                source.notify()

            elif attribute=="x_expr_enable":
                setattr(source,attribute,getattr(self,attribute).read())
                source.update_x_data(self.source_list[:])
                source.notify()

            elif attribute in ["y_expr"]:
                setattr(source,attribute,getattr(self,attribute).read())
                if not source.update_y_data(self.source_list[:]):
                    self.y_expr_enable.update(False)
                source.notify()

            elif attribute=="y_expr_enable":
                setattr(source,attribute,getattr(self,attribute).read())
                source.update_y_data(self.source_list[:])
                source.notify()

            elif attribute=="transpose":
                setattr(source,attribute,getattr(self,attribute).read())
                source.data=transpose(source.data)
                source.update_x_data(self.source_list[:])
                source.update_y_data(self.source_list[:])
                self.update_source_stuff()
                source.notify()

            elif attribute in ["norm_enable", "norm_min_pt", "norm_min_y", "norm_max_pt", "norm_max_y",
                              "scale_enable", "scale", "shift_enable", "shift", "name"]:
                try:
                    plot=self.plt_combo.get_selected_data()
                    plot.window.show_cursors=True
                except:
                    pass
                #print "jojo"
                setattr(source,attribute,getattr(self,attribute).read())

                if attribute=="norm_enable":
                    sel_source.update_y_data(self.source_list[:])
                    source.notify()

                elif attribute=="norm_min_pt":
                    if sel_source.norm_min_pt >= len(sel_source.x_data):
                        sel_source.morm_min_pt = len(sel_source.x_data)-1

                    self.norm_min_pt.set_valid()
                    self.norm_min_x.update(self.round_to_n(source.x_data[source.norm_min_pt],5))
                elif attribute=="norm_max_pt":

                    if sel_source.norm_max_pt >= len(sel_source.x_data):
                        sel_source.morm_max_pt = len(sel_source.x_data)-1

                    self.norm_max_pt.set_valid()
                    self.norm_max_x.update(self.round_to_n(source.x_data[source.norm_max_pt],5))

                if sel_source.norm_enable:
                    source.notify()
            #plots_to_update.union(source.notify())

        #for p in plots_to_update:
        #    p.window.update()


    def plt_proxy_updated(self,widget,attribute,value):
        #print "hej!"
        try:
            plot=self.plt_combo.get_selected_data()
        except:
            pass
        else:
            if attribute=="title":
                self.update_plt_title(plot)
        #        self.plt_combo.update(self.plt_proxy._get_model())
            elif attribute=="shown":
                if value:
                    #self.plt_combo.get_selected_data().window.window.activate_focus()
                    plot.window.show()
                else:
                    plot.window.window.destroy()
            elif attribute in ["xlim_min", "xlim_max"]:
                if plot.xlim_enable:
                    plot.window.update()
            elif attribute in ["ylim_min", "ylim_max"]:
                if plot.ylim_enable:
                    plot.window.update()
            elif attribute in ["xlim_enable", "ylim_enable"]:
                plot.window.update()
            elif attribute in ["x_axis_label", "x_axis_label_enable"]:
                if attribute == "x_axis_label":
                    if plot.x_axis_label_enable:
                        plot.window.update(limits=False, draw_canvas=False)
                else:
                    plot.window.update(limits=False, draw_canvas=False)
                plot.window.update_margins()

            elif attribute in ["y_axis_label", "y_axis_label_enable",]:
                if attribute == "y_axis_label":
                    if plot.y_axis_label_enable:
                        plot.window.update(limits=False, draw_canvas=False)
                else:
                    plot.window.update(limits=False, draw_canvas=False)
                plot.window.update_margins()
            elif attribute in ["x_grid_enable", "y_grid_enable",
                               "x_log_enable", "y_log_enable"]:
                plot.window.update(limits=False)

            elif "ticks" in attribute:
                plot.window.update_ticks()

            elif attribute in ["legend_enable"]:
                plot.window.update_legend()
                #self.plt_combo.get_selected_data().window.update()
            elif attribute in ["legend_loc", "legend_size",
                             "legend_border"]:
                plot.window.update_legend()
            elif attribute in ["figwidth"]:
                print "SETtING WIDTH"
                plot.window.figure.set_size_inches((value, plot.figheight), forward=True)
                #plot.window.canvas.show()


    def line_proxy_updated(self,widget,attribute,value):

        line=self.line_proxy._get_model()
        #setattr(line,attribute,getattr(self,attribute).read())

        if attribute in ["label"]:
            self.plt_proxy.model.window.update_legend()
        elif attribute in ["x_column", "y_column"]:
            self.plt_proxy.model.window.redraw([line.source], draw_canvas=False)
            self.plt_proxy.model.window.update()
            #self.plt_proxy.model.update()
        elif attribute in ["x_shift","y_shift","x_scale","y_scale"]:
            if getattr(line, attribute+"_enable"):
                self.plt_proxy.model.window.redraw([line.source], draw_canvas=False)
                self.plt_proxy.model.window.update()
        elif attribute in ["width", "style", "marker"]:
            line.update()
            self.plt_proxy.model.window.update_legend()
            #self.plt_proxy.model.window.legend

        else:
            #self.lines_list.update(self.line_proxy._get_model())
            self.plt_proxy.model.window.redraw([line.source], draw_canvas=False)
            self.plt_proxy.model.window.update()


#Source helpers

    def add_source(self, filename, parent=None, name="",
                   xcol=0, ycol=1, xexpr="x", yexpr="y",
                   xexpren=False, yexpren=False,
                   data=None):
        """Create a new source with (optional) data."""
        try:
            src=Source(id=self.src_id, datafile=filename, x_col=xcol, y_col=ycol,
                   x_expr=xexpr, y_expr=yexpr,
                   x_expr_enable=xexpren, y_expr_enable=yexpren,
                   data=data)
            self.source_list.append(src,select=True)
            self.src_id+=1
            #self.name.set_active()
        except SourceError:
            dialogs.error("Plothole was not able to load the input.",
                  filename+"\n\nIt expects text with numeric data in column format.")

    def add_sources(self, files):
        """Add several new sources."""
        for f in files:
            self.add_source(f)


    def rem_source(self, srcs=None):
        """Delete a source from the list."""
        if srcs is None:
            srcs=self.source_list.get_selected_rows()
        elif type(srcs) != list:
            srcs=[srcs]
        if not self.plt_combo.read() is ValueUnset:
            plts=self.plt_combo.get_model_items().values()
        else:
            plts=[]

        src_str=""
        for s in srcs:
            src_str+="<i>\'"+s.name+"\'</i> "
        reply=dialogs.yesno("You are about to remove "+str(len(srcs))+" Sources:\n"+\
                            src_str+".\n"\
                            "Is this what you want?")

        if reply == RESPONSE_YES:
            for src in srcs:
                plots=self.get_plots_with_source(src)
                for plot in plots:
                    plot.rem_line(plot.get_line(src))
                    self.lines_list.add_list(plot.lines)
                    self.update_plt_title(plot)
                self.source_list.remove(src)

    def add_folder(self, name="New folder"):
        fol=Folder(name=name)
        if fol:
            self.source_list.append(fol,select=True)

    def update_source_stuff(self):
        print "Updating source stuff...",
        instance=self.source_list.get_selected_rows()
        if len(instance) > 0:
            sel_source=instance[0]
            '''            s=self.source_list.get_next(sel_source)
            while not s==sel_source:
                print s.name
                if s.folder:
                    print self.source_list[self.source_list.index(s),0]
                s=self.source_list.get_next(s)'''
            nb=self.notebook.get_nth_page(0)
            #self.src_proxy.set_model(sel_source)

            self.statusbar.pop(self.context_id)

            self.source_pane.set_sensitive(True)
            if sel_source.folder:
                self.notebook.set_tab_label_text(nb,"Folder")
                self.expressions_expander.set_sensitive(False)
                self.normalize_expander.set_sensitive(False)
                self.comment_expander.set_sensitive(False)
                #self.file.set_sensitive(False)
                #self.x_col.set_sensitive(False)
                #self.y_col.set_sensitive(False)
            else:
                #if sel_source.file is not None:
                    #self.file.set_filename(sel_source.file)
                #else:
                    #pass
                    #self.file.prop_set_data_type(None)
                if sel_source.norm_enable:
                    self.norm_min_x.update(self.round_to_n(sel_source.x_data[sel_source.norm_min_pt],5))
                    self.norm_max_x.update(self.round_to_n(sel_source.x_data[sel_source.norm_max_pt],5))
                #self.notebook.set_tab_label_text(nb,"Source "+str(sel_source.id))
                self.update_gen_col_list(sel_source)
                if len(instance)==1:
                    self.statusbar.push(self.context_id, "Source "+
                                        str(sel_source.id)+": '"+
                                        sel_source.name+"', ("+
                                        str(len(sel_source.data))+
                                        " cols, "+str(len(sel_source.x_data))+
                                        " pts)")
                else:
                    self.statusbar.push(self.context_id, str(len(instance))+" sources selected")
                self.expressions_expander.set_sensitive(True)
                self.normalize_expander.set_sensitive(True)
                self.comment_expander.set_sensitive(True)
                #self.file.set_sensitive(True)
                #self.x_col.set_sensitive(True)
                #self.y_col.set_sensitive(True)

                #"""self.x_col.clear()
                #self.y_col.clear()
                ##for i,c in enumerate(sel_source.data):
                #    self.x_col.append_item(str(i), i)
                #    self.y_col.append_item(str(i), i)
                #print sel_source.name, sel_source.x_col, type(sel_source.x_col)
                #self.x_col.select_item_by_position(sel_source.x_col)
                #self.y_col.select_item_by_position(sel_source.y_col)

                print "Filling the column selectors..."
                self.loading=True
                #print sel_source.x_col, sel_source.y_col
                x_col=self.x_col.get_selected_data()
                y_col=self.y_col.get_selected_data()
                self.x_col.prefill(zip(map(str, range(len(sel_source.data))), range(len(sel_source.data))))
                self.y_col.prefill(zip(map(str, range(len(sel_source.data))), range(len(sel_source.data))))

                #self.notebook.set_current_page(0)

                #print x_col, y_col

                #self.x_col.select(x_col)
                #self.y_col.select(y_col)
                old_source=self.src_proxy.model
                old_source.x_col=x_col
                old_source.y_col=y_col

                self.src_proxy.set_model(sel_source)

                self.loading=False
                #self.src_proxy.set_model(sel_source)
        else:
            self.statusbar.pop(self.context_id)
            self.statusbar.push(self.context_id,"Total: <fixme>")

    def get_source_with_id(self, s_id):
        for s in self.source_list:
            if s.id == s_id:
                return s
        return None


#Plot helpers
    def add_plot_to_menu(self, plot):
        menuitem = gtk.MenuItem(plot.title)
        self.plotmenu.append(menuitem)
        menuitem.connect("activate", self.present_plot, plot.id)
        menuitem.show()


    def add_plot(self, sources):
        """Add a plot with sources"""
        plot_name="Plot"+str(self.plt_id)
        plot=Plot(self.plt_id, plot_name, sources, show=False, parent=self)
        self.plt_id+=1

        self.plt_combo.append_item(plot_name+" ("+str(len(sources))+")", plot)
        self.plt_combo.select_item_by_data(plot)

        self.lines_list.add_list(plot.lines)
        plot.window.show()
        #self.lines_list.select(self.lines_list[0])


    def get_plots_with_source(self, src):
        """Returns list of all plots containing src"""
        plots=[]
        for r in self.plot_model:
            p=r[ComboColumn.DATA]
            for l in p.lines:
                if src==l.source:
                    plots.append(p)
        return plots

    def remove_plot(self):
        """Remove the current plot from the program"""

        #close the plot window
        curr_plot=self.plt_combo.get_selected_data()
        if curr_plot.window.window is not None:
            curr_plot.window.destroy_cb(None)

        #probably not a very efficient way of doing this...
        self.loading=True
        plt_keys=self.plt_combo.get_model_items().keys()
        plt_values=self.plt_combo.get_model_items().values()
        sel_index=plt_values.index(curr_plot)
        print plt_keys
        print plt_values
        plt_keys.remove(plt_keys[sel_index])
        plt_values.remove(curr_plot)

        self.plt_combo.clear()
        self.plt_combo.prefill(zip(plt_keys,plt_values))
        self.loading=False

        # self.plt_combo.select_item_by_position(0)
        # plot=self.plt_combo.get_selected_data()
        # if plot is not None:
            # for s in self.source_list:
                # s.toggle=(s in plot.get_lines_sources())
        # else:
            # for s in self.source_list:
                # s.toggle=False
        #
        self.update_plot_stuff()

    def close_all_plots(self):
        if len(self.plt_combo) > 0:
            plots=self.plt_combo.get_model_items().values()
            for p in plots:
                if p.window is not None and p.window.window is not None:
                    p.window.destroy_cb(None)

    def present_plot(self, plot):
        if type(plot) == int:
            plot=self.get_plot
        if plot.shown and not self.loading:
            #self.notebook.set_current_page(1)
            if plot.window is not None:
                if not plot.window.window.get_property('is-active'):
                #time.sleep(1)
                    print "on_plt_combo_changed:", widget.get_selected_data().title
                    plot.window.window.present()


    def update_plt_title(self, plot):
        """probably not a very efficient way of doing this..."""

        self.loading=True
        #curr_plot=self.plt_combo.get_selected_data()
        curr_plot=plot
        plt_keys=self.plt_combo.get_model_items().keys()
        plt_values=self.plt_combo.get_model_items().values()
        sel_index=plt_values.index(plot)
        title=plot.title
        #ellipsize very long plot titles
        title = self.ellipsize(title, 20)

        plt_keys[sel_index]=title+" ("+str(len(plot.lines))+")"
        self.plt_combo.clear()
        self.plt_combo.prefill(zip(plt_keys,plt_values))
        self.plt_combo.select_item_by_data(curr_plot)
        #update window titles
        if plot.window.window is not None:
            plot.window.window.set_title(plot.title)
        self.loading=False

    def update_plot_stuff(self):
        plot=self.plt_combo.get_selected_data()
        if plot:
            self.plt_proxy.set_model(plot)
            for s in self.source_list:
                s.toggle=(s in plot.get_lines_sources())
            self.source_list.refresh()
            nb=self.notebook.get_nth_page(1)
            #self.notebook.set_tab_label_text(nb,"Plot "+str(plot.id))
            self.lines_list.clear()
            self.lines_list.add_list(plot.lines)
            self.lines_list.select(self.lines_list[0])
            self.plot_pane.set_sensitive(True)
            if len(plot.lines) == 0:
                self.line_notebook.set_sensitive(False)
            else:
                self.line_notebook.set_sensitive(True)
            if plot.shown and not self.loading:
                self.notebook.set_current_page(1)
                if plot.window is not None:
                    if not plot.window.window.get_property('is-active'):
                    #time.sleep(1)
                        plot.window.window.present()
        else:
            self.notebook.set_tab_label_text(self.notebook.get_nth_page(1),"(No Plot)")
            self.lines_list.clear()
            for s in self.source_list:
                s.toggle=False
            self.plot_pane.set_sensitive(False)

        self.source_list.refresh()

    def get_plot_with_id(self, p_id):
        return self.plots[self.plots.index(p_id)]


#Line helpers
    def add_line(self, src, plot=None, show=True):
        if plot is None:
            curr_plot=self.plt_combo.get_selected_data()
        else:
            curr_plot=plot
        curr_plot.add_line(src, show=show)
        self.lines_list.add_list(curr_plot.lines)
        #self.plt_combo.set_selected_name(curr_plot.name+" ("+str(len(curr_plot.sources))+")")
        self.update_plt_title(curr_plot)
        #for s in self.source_list[:]:
        #    if s.folder:
        #        print self.source_list[self.source_list.index(s)][:]
        #    else:
        #        print s


    def remove_line(self, src):
        curr_plot=self.plt_combo.get_selected_data()
        curr_plot.rem_line(curr_plot.get_line(src))
        self.lines_list.add_list(curr_plot.lines)
        self.update_plt_title(curr_plot)

#Other helpers
    def ellipsize(self, str, length):
        """Ellipsize a string after a certin length."""
        if len(str) > length:
            str = str[:length]+"..."
        return str

    def update_gen_col_list(self, source):
        self.gen_col_list.clear()
        self.gen_col_list.add_list(source.gen_cols)


#UI callbacks etc
    def on_x_axis_label__activate(self, widget):
        plot=self.plt_combo.get_selected_data()
        self.x_axis_label_enable.update(True)
    def on_y_axis_label__activate(self, widget):
        plot=self.plt_combo.get_selected_data()
        self.y_axis_label_enable.update(True)
    def on_x_expr_activated(self, widget):
        """Runs when the user presses Return in the x Expression widget"""
        self.x_expr_enable.update(True)
    def on_y_expr_activated(self, widget):
        """Runs when the user presses Return in the y Expression widget"""
        self.y_expr_enable.update(True)
    #*** Callbacks ***

    def on_drag_data_received(self, widget, drag_context, x, y, selection_data, info, time):
        print selection_data
        for data in selection_data.data.split("file://"):
            if len(data)>0:
                if data[2] == ":":
                    data = data[1:]  #remove extra slash if on windows
                    while ord(data[-1])<16:
                        data = data[:-1]  #remove trailing trash
                self.add_source(str(unquote(data.rstrip("\r\n")).decode("utf-8"))) #seems to avoid unicode trouble on windows
        drag_context.finish(True, False, time)


    def on_source_list__selection_changed(self,entries,instance):
        self.update_source_stuff()


    def on_lines_list__selection_changed(self,entries,instance):
        if not instance is ValueUnset:
            print "instance="+str(instance)
            sel_source=instance
            self.line_proxy.set_model(sel_source)
            self.line_notebook.set_sensitive(True)

            if instance is not None:
                self.color=gtk.gdk.Color(
                    int(self.line_proxy.model.color[0]*65535),
                    int(self.line_proxy.model.color[1]*65535),
                    int(self.line_proxy.model.color[2]*65535)
                    )
            self.line_color_area.modify_bg(gtk.STATE_NORMAL, self.color)
        else:
            self.line_notebook.set_sensitive(False)


    # def on_file__file_set(self,widget):
        # if widget.get_filename():
            # source=self.src_proxy._get_model()
            # source.file=widget.get_filename()
            # source.load_data()
            # source.update_x_data(self.source_list)
            # source.update_y_data(self.source_list)
            # self.source_list.update(source)
            # for plot in self.get_plots_with_source(source):
                # plot.window.update()

    #    def on_new_plot__clicked(self, widget):
    #        print "plot"
    #        sel_sources=self.source_list.get_selected_rows()
    #        self.add_plot(sel_sources)

    #    def on_delete_plot__clicked(self,widget):
    #        print "deleting plot..."
    #        self.remove_plot()
    def on_refresh_plot__clicked(self, widget):
        self.plt_proxy.model.window.draw()
        self.plt_proxy.model.window.update()

    def on_gen_col_add__clicked(self, widget):
        source=self.source_list.get_selected_rows()[0]
        gen_col=GeneratedColumn(source, id=source.next_gen_col_id())
        source.gen_cols.append(gen_col)
        self.update_gen_col_list(source)

    def on_line_up__clicked(self, widget):
        plot=self.plt_proxy.model
        line=self.line_proxy.model
        ind=plot.lines.index(line)
        if ind in arange(1, len(plot.lines)):
            plot.lines.remove(line)
            plot.lines.insert(ind-1, line)

            plot.window.axes.lines.remove(line.handle)
            plot.window.axes.lines.insert(ind-1, line.handle)

            self.lines_list.clear()
            self.lines_list.add_list(plot.lines)
            self.lines_list.select(line)

            plot.window.update_legend()

    def on_xlim_all__clicked(self, widget):
        print "xlim_all clicked"

    def on_line_down__clicked(self, widget):
        plot=self.plt_proxy.model
        line=self.line_proxy.model
        ind=plot.lines.index(line)
        if ind in arange(0, len(plot.lines)-1):
            plot.lines.remove(line)
            plot.lines.insert(ind+1, line)

            plot.window.axes.lines.remove(line.handle)
            plot.window.axes.lines.insert(ind+1, line.handle)

            self.lines_list.clear()
            self.lines_list.add_list(plot.lines)
            self.lines_list.select(line)

            plot.window.update_legend()


    #    def on_title__content_changed(self,widget):
    #        print("hej")

    def color_changed_cb(self, widget):
        # Get drawingarea colormap
        self.line_colormap = self.line_color_area.get_colormap()

        # Get current color
        self.line_color = self.line_colorseldlg.colorsel.get_current_color()
        self.line_proxy.model.color=(
            self.line_color.red/65535.0,
            self.line_color.green/65535.0,
            self.line_color.blue/65535.0
            )
        #print self.line_proxy.model.color
        line=self.line_proxy.model
        line.update()

        self.plt_proxy.model.window.update_legend()
        self.plt_proxy.model.window.canvas.draw()

        # Set button background color
        self.line_color_area.modify_bg(gtk.STATE_NORMAL, self.line_color)

    """def on_x_col_combo__changed(self, widget):
        if not self.loading:
            source=self.source_list.get_selected_rows()[0]
            source.x_col=widget.get_selected_data()
            source.notify()
            print "x_col_changed!"

    def on_y_col_combo__changed(self, widget):
        if not self.loading:
            source=self.source_list.get_selected_rows()[0]
            source.y_col=widget.get_selected_data()
            source.notify()
            print "y_col_changed!"""


    def on_plt_combo__changed(self, widget):
        if not self.loading:
            #print "changed plot:", self.plt_combo.get_selected_data().title
            plot=widget.get_selected_data()
            if plot:
                self.plt_proxy.set_model(plot)
                for s in self.source_list:
                    s.toggle=(s in plot.get_lines_sources())
                self.source_list.refresh()
                nb=self.notebook.get_nth_page(1)
                #self.notebook.set_tab_label_text(nb,"Plot "+str(plot.id))
                self.lines_list.clear()
                self.lines_list.add_list(plot.lines)
                self.lines_list.select(self.lines_list[0])
                self.plot_pane.set_sensitive(True)
                if len(plot.lines) == 0:
                    print "nwpp"
                    self.line_notebook.set_sensitive(False)
                else:
                    print "flepp"
                    self.line_notebook.set_sensitive(True)
                if plot.shown and not self.loading:
                    #self.notebook.set_current_page(1)
                    if plot.window is not None:
                        if not plot.window.window.get_property('is-active'):
                        #time.sleep(1)
                            print "on_plt_combo_changed:", widget.get_selected_data().title
                            plot.window.window.present()
            else:
                self.plot_pane.set_sensitive(False)

    def on_gen_col_list__cell_edited(self, widget, row, shoe):
        if row.enabled:
            row.update_data(self.source_list[:])
        else:
            widget.refresh()

    # Drawingarea event handler
    def line_color_area_event(self, widget, event):
        handled = False

        # Check if we've received a button pressed event
        if event.type == gtk.gdk.BUTTON_PRESS:
            handled = True
            # Create color selection dialog
            if self.line_colorseldlg == None:
                self.line_colorseldlg = gtk.ColorSelectionDialog(
                    "Select line color")

            # Get the ColorSelection widget
            colorsel = self.line_colorseldlg.colorsel

            colorsel.set_previous_color(self.color)
            colorsel.set_current_color(self.color)
            colorsel.set_has_palette(True)

            # Connect to the "color_changed" signal
            # colorsel.connect("color_changed", self.color_changed_cb)
            # Show the dialog
            response = self.line_colorseldlg.run()

            if response -- gtk.RESPONSE_OK:
                self.color = colorsel.get_current_color()
                self.line_color_area.modify_bg(gtk.STATE_NORMAL, self.color)
                self.line_proxy.model.color=(
                    self.color.red/65535.0,
                    self.color.green/65535.0,
                    self.color.blue/65535.0
                    )
                self.line_proxy.model.update()
                self.plt_proxy.model.window.canvas.draw()
                self.plt_proxy.model.window.update_legend()

    #            else:
    #                self.line_color_area.modify_bg(gtk.STATE_NORMAL, self.color)

            self.line_colorseldlg.hide()

        return handled



    def on_source_list__cell_edited(self,widget,row,col):
        if col == "toggle":
            if row.toggle:
                if len(self.plt_combo):
                    print row
                    self.add_line(row)
                else:
                    self.add_plot([row])

            else:
                if len(self.plt_combo):
                    self.remove_line(row)
        #elif col == "name":
        #    row.name=

    def on_normalize_expander__activate(self,widget):
        print "hello"
        source=self.source_list.get_selected_rows()[0]
        try:
            plot=self.plt_combo.get_selected_data()
            if plot.window.show_cursors:
                plot.window.show_cursors=False
            else:
                plot.window.show_cursors=True
            if source.norm_enable:
                source.notify()
        except:
            pass

    def on_normalize_expander__hide(self,widget):
        print "bye!"


    #Menu actions (placeholders)

    def save_cb(self, w):
        if self.session_file is None:
            filename=dialogs.save()
            self.session_file=self.save_session(filename)
            self.set_title("Plothole: "+os.path.split(self.session_file)[-1])
        else:
            filename=self.save_session(self.session_file)
            if filename is not None:
                self.session_file=filename
                self.set_title("Plothole: "+os.path.split(self.session_file)[-1])

    def save_as_cb(self,w):
        #self.session_file=file_browse(gtk.FILE_CHOOSER_ACTION_SAVE)
        filename=dialogs.save()
        if filename:
            filename=self.save_session(filename)
            if filename is not None:
                self.session_file=filename
                self.set_title("Plothole: "+os.path.split(self.session_file)[-1])

    def load_cb(self, w):
        #filename=file_browse(gtk.FILE_CHOOSER_ACTION_OPEN)
        filename=dialogs.open(patterns=["*.plh"])
        self.load_session(filename)
        self.session_file=filename
        self.set_title("Plothole: "+os.path.split(filename)[-1])

    def export_source_cb(self, w):
        filename = dialogs.save()
        sel_source=self.source_list.get_selected_rows()[0]
        savetxt(filename, transpose(array([sel_source.x_data, sel_source.y_data])), delimiter="\t")

    def mute_cb(self, w):
        pass

    def quit_cb(self, w):
        pass

    def add_source_cb(self, w):
        self.add_source(None,data=None)

    def add_source_from_file_cb(self, w):
        filename = dialogs.open()
        with open(filename) as f:
            text = f.read()
            self.add_source(None, data=load_data(None, datastr=text))

    def add_source_from_clipboard_cb(self, w):
        text = self.clipboard.wait_for_text()
        if text != "":
            self.add_source(None, data=load_data(None, datastr=text))

    def rem_source_cb(self, w):
        w=self.get_focus_widget()
        if w==self.source_listview:
            self.rem_source()
        else:
    #            if w.get_editable():
            print "hej"
            pos=w.get_position()
            print pos
            w.delete_text(pos,pos+1)

    def dup_source_cb(self, w):
        sel_sources=self.source_list.get_selected_rows()
        for s in sel_sources:
            self.add_source(s.file, name=s.name, xcol=s.x_col, ycol=s.y_col,
                        xexpr=s.x_expr, yexpr=s.y_expr,
                        xexpren=s.x_expr_enable, yexpren=s.y_expr_enable)

    def select_plot_sources(self, w):
        pass

    def add_folder_cb(self, w):
        self.add_folder(name="New folder")

    def copy_cb(self,w):
        w=self.get_focus_widget()
        if w==self.source_listview:
            pass
            #sel_sources=self.source_list.get_selected_rows()
            #self.src_clipboard=sel_sources
        else:
            #if w.editable:
            w.copy_clipboard()

    def cut_cb(self,w):
        w=self.get_focus_widget()
        if w==self.source_listview:
            pass
            #sel_sources=self.source_list.get_selected_rows()
            #self.src_clipboard=sel_sources
            #self.src_clipboard_cut=True
        else:
            #if w.editable:
            w.copy_clipboard()

    def paste_cb(self,w):
        w=self.get_focus_widget()
        if w==self.source_listview:
            pass
            #sel_source=self.source_list.get_selected_rows()[0]
            #if sel_source.folder:
            #    for s in self.src_clipboard:
            #        if sel_source.folder:
            #            parent=sel_source
            #        else:
            #            parent=None
            #        self.add_source(s.file, parent=parent, name=s.name, xcol=s.x_col, ycol=s.y_col, xexpr=s.x_expr, yexpr=s.y_expr, xexpren=s.x_expr_enable, yexpren=s.y_expr_enable)
            #if self.src_clipboard_cut:
            #    self.rem_source(self.src_clipboard)
            #    self.src_clipboard_cut=False
        else:
            #if w.editable:
            w.paste_clipboard()

    def new_plot_cb(self,w):
        sel_sources=self.source_list.get_selected_rows()
        self.add_plot(sel_sources)

    def del_plot_cb(self, w):
        self.remove_plot()

    def save_session(self,file=""):
        """Called when the user wants to save a wine list"""

        # Get the File Save path

        # We have a path, ensure the proper extension
        save_file, extension = os.path.splitext(file)
        save_file = save_file + "." + FILE_EXT
        print extension, save_file
        """ Now we have the "real" file save loction create
        the shelve file, use "n" to create a new file"""
        db = shelve.open(save_file,"n")

        db["sources"] = self.source_list[:]

        plots=[]
        plotwins=[]
        for r in self.plot_model:
            p=r[ComboColumn.DATA]
            print p.title
            plots.append(p)
        db["plots"]=plots

        db["source_id"]=self.src_id
        db["plot_id"]=self.plt_id
        db.close()
        #set the project file
        return save_file

    def load_session(self, filename):
        self.loading=True
        if (filename != ""):
            db=shelve.open(filename,"r")
            if db:
                for k in db.keys():
                    print k, db[k]
                #added_plot_ids=[]
                sources=db["sources"]
                newsources=[]
                for s in sources:
                    news=Source()
                    for sitem in s.__dict__.keys():
                        setattr(news, sitem, s.__dict__[sitem])
                    newsources.append(news)

                self.source_list._load(newsources, True)
                plots=db["plots"]
                plots.sort()
                pl=[]
                self.close_all_plots()
                self.plt_combo.clear()
                for p in plots:
                    print "Loading:", p.title

                    newp=Plot(id=p.id, title=p.title, parent=self)
                    for item in p.__dict__.keys():
                        setattr(newp, item, p.__dict__[item])

                    for i, l in enumerate(newp.lines):

                        newl=Line()
                        for litem in l.__dict__.keys():
                            setattr(newl, litem, l.__dict__[litem])
                        newl.plot=newp
                        newl.source=self.get_source_with_id(l.source)
                        newl.source.attach(newl)
                        #newl.source.update_x_data(self.source_list[:])
                        #newl.source.update_y_data(self.source_list[:])
                        newp.lines[i]=newl

                    newp.parent=self
                    newp.create_window()
    #                    if p.shown:
    #                        p.window.window.move(p.window_pos[0], p.window_pos[1])
    #                        p.window.window.resize(p.window_size[0], p.window_size[1])
                    self.plt_combo.append_item(self.ellipsize(p.title, 20), data=newp)
                    self.plt_combo.select_item_by_position(0)
                    self.update_plt_title(newp)
                    self.plt_proxy.set_model(newp)
                    self.lines_list.clear()
                    self.lines_list.add_list(newp.lines)
                    #self.lines_list.select(self.lines_list[0])
                    self.plot_pane.set_sensitive(True)
                    self.line_notebook.set_sensitive(True)

    #                keys=db.keys()
    #                keys.remove("active_plo

    #                self.plot_list.set_active(db["active_plot"])
                self.src_id=db["source_id"]
                self.plt_id=db["plot_id"]
                #self.source_list.update()
    #                for p in plots:
    #                    if p.shown:
    #                        p.window.show()
                #self.plt_combo.update()

                #self.update_plt_title(p)

                db.close()

                #self.plt_combo.select_item_by_position(0)
                p=self.plt_combo.get_selected_data()
                for s in self.source_list:
                    s.toggle=(s in p.get_lines_sources())

                self.source_list.refresh()

        self.loading=False

    def destroy(self, widget, data=None):
        gtk.main_quit()


import cProfile

delegate = PlotHole()
delegate.show()

#cProfile.run('gtk.main()', "plothole.prof")
gtk.main()
