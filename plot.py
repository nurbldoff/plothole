from __future__ import division
from kiwi.model import Model
import copy
import types
import sys

try:
    import pygtk
    pygtk.require("2.0")
except:
    pass
try:
    import gtk
    import gtk.glade
except:
    sys.exit(1)

import gobject
import pylab
#from pylab import   popopo*
from pylab import show, axes
from numpy import transpose, array #, min, max
from matplotlib.axes import Subplot
from matplotlib.font_manager import FontProperties
from matplotlib.figure import Figure
#from matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo as FigureCanvas
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
#from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas


from matplotlib.backends.backend_gtk import NavigationToolbar2GTK as NavigationToolbar
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, ScalarFormatter, MaxNLocator, NullLocator
from matplotlib.widgets import RectangleSelector, Button
from matplotlib.lines import Line2D
from matplotlib.legend import Legend
#from matplotlib.cbook import CallbackRegistry

#from numpy import min, max

def round_to_n(x,n):
    """Rounds x to n significant digits"""
    if n < 1:
        raise ValueError("number of significant digits must be >= 1")
    return float("%.*e" % (n-1, x))

class PlotObject:
    pass

class Line:
    def __init__(self, src=None, plot=None, x_column=0, y_column=1, label="", style="-", marker="None", color="", width=1.0, lid=-1,
                 x_scale_enable=False, x_scale=1.0,
                 y_scale_enable=False, y_scale=1.0,
                 x_shift_enable=False, x_shift=0.0,
                 y_shift_enable=False, y_shift=0.0,
                 ):
        self.id=lid
        self.source=src
        self.plot=plot
        self.x_column=x_column
        self.y_column=y_column
        if label=="":
            if self.source:
                self.label=self.source.name
            else:
                if id>-1:
                    self.label="Line"+str(self.id)
                else:
                    self.label=""
        else:
            self.label=label

        self.style=style
        self.marker=marker

        self.source_columns_enable=True
        if color:
            self.color=color
        else:
            self.color=[
                (1.,0,0),
                (0,1.,0),
                (0,0,1.),
                (0,1.,1.),
                (1.,0,1.),
                (1.,1.,0),
                (0,0,0)] [self.id%7]

        self.width=width
        self.handle=None

        self.x_scale_enable=x_scale_enable
        self.x_scale=x_scale
        self.y_scale_enable=y_scale_enable
        self.y_scale=y_scale
        self.x_shift_enable=x_shift_enable
        self.x_shift=x_shift
        self.y_shift_enable=y_shift_enable
        self.y_shift=y_shift

    def __getstate__(self):
        d=copy.copy(self.__dict__)
        d["handle"]=None
        d["source"]=self.source.id
        for item in d:
            if type(d[item])==types.FunctionType:
                del(d[item])

        return d

    def redraw(self):
        #self.plot.window.draw_line(self)
        print "Redrawing line %d in plot %d"%(self.id, self.plot.id)
        self.plot.window.redraw([self.source], draw_canvas=True)
        #return self.plot

    def update(self):
        self.handle.set_color(self.color)
        self.handle.set_linestyle(self.style)
        self.handle.set_marker(self.marker)
        self.handle.set_linewidth(self.width)

    def get_data(self):
        if self.source_columns_enable:
            x_data=self.source.x_data
        elif self.x_column >= len(self.source.data):
            x_data=self.source.gen_cols[self.x_column-len(self.source.data)].data
        else:
            x_data=self.source.data[self.x_column]

        if self.source_columns_enable:
            y_data=self.source.y_data
        elif self.y_column >= len(self.source.data):
            y_data=self.source.gen_cols[self.y_column-len(self.source.data)].data
        else:
            y_data=self.source.data[self.y_column]

        if self.source.norm_enable:
            y_data=(y_data-y_data[self.source.norm_min_pt])/\
                    (y_data[self.source.norm_max_pt]-\
                    y_data[self.source.norm_min_pt])*\
                    (self.source.norm_max_y-self.source.norm_min_y)+self.source.norm_min_y

        if self.x_scale_enable:
            x_data=x_data*self.x_scale
        if self.y_scale_enable:
            y_data=y_data*self.y_scale
        if self.x_shift_enable:
            x_data=x_data+self.x_shift
        if self.y_shift_enable:
            y_data=y_data+self.y_shift

        return (x_data, y_data)

    def update_extremes(self):
        print "updating extremes"
        x_data, y_data=self.get_data()
        self.extremes=array([
            min(x_data), max(x_data),
            min(y_data), max(y_data),
            ])

    def get_extremes(self):
        #print "updating extremes"
        x_data, y_data=self.get_data()
        #print y_data, max(y_data)
        extr=[ min(x_data), max(x_data), min(y_data), max(y_data) ]
        #print "line.get_extremes-> "+str(extr)
        return extr


#    def __getattr__(self, att):
#        if att == 'id':
#            return self.source.id
#        else:  raise AttributeError, att


class Plot:
    def __init__(self, id=0, title="", sources=[], show=False, mpl="", parent=None):
        self.id=id
        self.title=title
        self.lines=[]
        self.line_id=0

        self.legend_enable=True
        self.legend_loc="best"
        self.legend_size="medium"
        self.legend_border=False

        self.xlim_enable=False
        self.ylim_enable=False
        self.xlim_min=None
        self.xlim_max=None
        self.ylim_min=None
        self.ylim_max=None

        self.x_log_enable=False
        self.y_log_enable=False

        self.x_axis_label_enable=False
        self.x_axis_label=""
        self.y_axis_label_enable=False
        self.y_axis_label=""

        self.x_grid_enable=False
        self.y_grid_enable=False

        self.x_majorticks_enable=True
        self.y_majorticks_enable=True
        self.x_majorticks_maxn=10
        self.y_majorticks_maxn=10

        self.x_minorticks_enable=False
        self.y_minorticks_enable=False
        self.x_minorticks_maxn=20
        self.y_minorticks_maxn=20

        self.shown=show
        self.mpl_commands=mpl
        #self.window=None
        self.parent=parent

        self.window_size=(0,0)
        self.window_pos=(0,0)

        self.figwidth=0.
        self.figheight=0.

        for src in sources:
            self.add_line(src, show=False)

        self.create_window()

        #self.window.show()

    def __getstate__(self):
        d=copy.copy(self.__dict__)
        d["window"]=None
        d["parent"]=None
        for item in d:
            if type(d[item])==types.FunctionType:
                del(d[item])
        return d

    def __setstate__(self, newstate):
       for item in newstate.keys():
           self.__dict__[item]=newstate[item]
        #self.__init__()
#    def __cmp__(self, other):
#        return cmp(self.id, other.id)

    def create_window(self):
        self.window=PlotWindow(self, title=self.title, lines=self.lines, shown=self.shown)
        #self.window.show()

    def add_line(self, src, show=True):
        line = Line(src, self, src.x_col, src.y_col, lid=self.line_id)
        line.update_extremes()
        self.lines.append(line)
        src.attach(line)
        #src.plots.append(self)
        self.line_id += 1
        if show:
            self.window.draw_line(line, draw_canvas=False)
            self.window.update_legend(draw_canvas=False)
            self.window.update(limits=True)
        return line

    def rem_line(self, line):
    #        line.handle.remove()
        #line.source.plots.remove(self)
        self.lines.remove(line)
        line.source.detach(line)
        self.window.axes.lines.remove(line.handle)
        if self.shown:
            self.window.update_legend(draw_canvas=False)
            self.window.update()
        #return line

    def get_lines_sources(self):
        #s=[]
        #for l in self.lines:
        #    s.append(l.source)
        return (l.source for l in self.lines)

    def get_line(self, src):
        for l in self.lines:
            if l.source==src:
                return l

    def get_extremes(self):
        m=[]
        for l in self.lines:
            m.append(l.get_extremes())
        m=transpose(array(m))
        #print "m: ", m
        if len(m) > 0:
            #print [min(m[0]), max(m[1]), min(m[2]), max(m[3])]
            return array([min(m[0]), max(m[1]), min(m[2]), max(m[3])])
        else:
            return m

def legend_picker(artist, event):
    print "Event:", event.x, event.y
    print "BBox:", artist.get_window_extent().xmin, artist.get_window_extent().xmax
    return (artist.get_window_extent().contains(event.x,event.y), {})

def axis_picker(artist, event):
    print "Event:", event.x, event.y
    #print "BBox:", artist.get_window_extent().xmin, artist.get_window_extent().xmax
    #return (artist.get_window_extent().contains(event.x,event.y), {})

class PlotWindow:
    def __init__(self, plot, title="", lines=[], shown=False):

        self.plot=plot

        self.window=None
        self.vbox=None
        self.figure=None
        self.canvas=None
        self.axes=None
        self.legend=None

        self.show_cursors=False

        self.plot.shown=shown
        if shown:
            self.show()


    def show(self):
        self.vbox = gtk.VBox()
        self.figure = Figure(figsize=(5,4))

        self.figure.set_size_inches(self.plot.figwidth, self.plot.figheight)

        self.window = gtk.Window()
        self.window.connect("destroy", self.destroy_cb)
    #        self.window.connect("set-focus", self.set_focus_cb)
        self.window.connect("notify::is-active", self.window_focus_cb)
        self.window.add(self.vbox)

        self.canvas = FigureCanvas(self.figure)  # a gtk.DrawingArea

        self.draw()
        self.update(limits=True)

        self.vbox.pack_start(self.canvas)

        toolbar = NavigationToolbar(self.canvas, self.window)
        self.vbox.pack_start(toolbar, False, False)

        if self.plot.window_size != (0,0):
            self.window.resize(self.plot.window_size[0],
                               self.plot.window_size[1])
        else:
            self.window.resize(400, 300)
        if self.plot.window_pos != (0,0):
            self.window.move(self.plot.window_pos[0],
                             self.plot.window_pos[1])

        self.window.set_title(self.plot.title)

        self.cursors, = self.axes.plot(self.plot.lines[0].get_data()[0], self.plot.lines[0].get_data()[1])
        self.cursors.set_linestyle("None")
        self.cursors.set_markersize(10)
        self.cursors.set_markeredgewidth(2)
        self.cursors.set_markeredgecolor("k")
        self.cursors.set_antialiased(False)

        self.window.show_all()

#        self.plot.figwidth=self.figure.get_figwidth()
#        self.plot.figheight=self.figure.get_figheight()



        #   self.pos=self.window.get_position()
        self.plot.shown=True

    def set_focus_cb(self,window,data):
        print "Hej!"

    def window_focus_cb(self,window,data):
        print self.plot.window_size, self.plot.window_pos
        print "window_focus_cb:", self.plot.title
        if window.get_property('is-active'):
            #self.plot.parent.notebook.set_current_page(1)
            print "is-active"
            if self.plot.parent.plt_combo.get_selected_data() != self.plot:
                print "selecting item..."
                self.plot.parent.plt_combo.select_item_by_data(self.plot)
            self.plot.window_size=self.window.get_size()
            self.plot.window_pos=self.window.get_position()

            self.plot.figwidth=self.figure.get_figwidth()
            self.plot.figheight=self.figure.get_figheight()

    def draw(self, items=None, sources=None):
        legend=[]
        print "drawing "+self.plot.title
        def myfmt(x,y): return 'x=%1.6g\ny=%1.6g'%(x,y)
        self.figure.clf()
        self.axes = self.figure.add_subplot(111)
        #self.axes = self.figure.add_axes([0.10,0.10,0.85,0.85])
        #self.figure.subplots_adjust(bottom=0.15, left=0.15)
        self.axes.set_autoscale_on(False)
        self.axes.format_coord = myfmt

    #        self.btn_axes=self.figure.add_axes([0,0,0.1,0.05], frameon=True)
    #        self.cursor_a_btn=Button(self.btn_axes,"A")

        #self.selector=RectangleSelector(self.axes, self.rectangle_cb, useblit=True)
        self.canvas.mpl_connect('button_release_event', self.button_up_cb)

        #self.axes.callbacks.connect("xlim_changed",self.xlim_cb)
        #self.axes.callbacks.connect("ylim_changed",self.ylim_cb)
        self.figure.canvas.mpl_connect('pick_event',self.pick_cb)

        # xaxis=self.axes.get_xaxis()
        # yaxis=self.axes.get_yaxis()

        # xaxis.set_picker(axis_picker)
        # yaxis.set_picker(axis_picker)


        legend=[]

        for line in self.plot.lines:
            self.draw_line(line, draw_canvas=False)
            #source=line.source
            # if line.source is not None:
                # x_data, y_data=line.get_data()

                # line.handle, = self.axes.plot(x_data, y_data,
                                           # color=line.color, ls=line.style,
                                           # linewidth=line.width, picker=5.0)
                                           # #data_clipping=True)
                # line.handle.parent=line
                # legend.append(line.label)
                # #line.handle.set_label(line.label)

        #self.update()


        self.update_legend(draw_canvas=False)
        self.update_ticks(draw_canvas=False)

        self.canvas.draw()

    def draw_line(self, line, draw_canvas=True):
        #source=line.source
        if line.source is not None:
            x_data, y_data=line.get_data()

            line.handle, = self.axes.plot(x_data, y_data,
                                       color=line.color, ls=line.style,
                                       marker= line.marker, mew=0,
                                       linewidth=line.width, picker=5.0,
                                       label=line.label)
                                       #data_clipping=True)
            line.handle.parent=line
            #legend.append(line.label)
            #line.handle.set_label(line.label)

        #self.update()
        if draw_canvas:
            self.canvas.draw()

    def update_ticks(self, draw_canvas=True):

        xMajorFormatter = ScalarFormatter()
        yMajorFormatter = ScalarFormatter()
        xMajorFormatter.set_powerlimits((-3,4))
        yMajorFormatter.set_powerlimits((-3,4))

        xaxis=self.axes.get_xaxis()
        yaxis=self.axes.get_yaxis()

        xaxis.set_major_formatter(xMajorFormatter)
        yaxis.set_major_formatter(yMajorFormatter)

        if self.plot.x_majorticks_enable:
            xMajorLocator = MaxNLocator(self.plot.x_majorticks_maxn)
            xaxis.set_major_locator(xMajorLocator)
        else:
            xaxis.set_major_locator(NullLocator())

        if self.plot.y_majorticks_enable:
            yMajorLocator = MaxNLocator(self.plot.y_majorticks_maxn)
            yaxis.set_major_locator(yMajorLocator)
        else:
            yaxis.set_major_locator(NullLocator())

        if self.plot.x_minorticks_enable:
            xMinorLocator = MaxNLocator(self.plot.x_minorticks_maxn)
            xaxis.set_minor_locator(xMinorLocator)
        else:
            xaxis.set_minor_locator(NullLocator())

        if self.plot.y_minorticks_enable:
            yMinorLocator = MaxNLocator(self.plot.y_minorticks_maxn)
            yaxis.set_minor_locator(yMinorLocator)
        else:
            yaxis.set_minor_locator(NullLocator())

        self.update_margins(draw_canvas=False)

        if draw_canvas:
            self.canvas.draw()

    def update_margins(self, draw_canvas=True):

        margins={"left":0.05, "bottom":0.05}

        if self.plot.x_axis_label_enable:
            margins["bottom"]+=0.05
        if self.plot.y_axis_label_enable:
            margins["left"]+=0.05
        if self.plot.x_majorticks_enable:
            margins["bottom"]+=0.05
        if self.plot.y_majorticks_enable:
            margins["left"]+=0.05

        print margins

        self.figure.subplots_adjust(**margins)

        if draw_canvas:
            self.canvas.draw()

    def update_legend(self, draw_canvas=True):
        if self.plot.legend_enable:
            print "update_legend()"
            lines=[]
            labels=[]
            for line in self.plot.lines:
                labels.append(line.label)
                lines.append(line.handle)
                #line.handle.set_label(line.label)

            self.legend=self.axes.legend(lines, labels, loc=self.plot.legend_loc,
                               prop=FontProperties(size=self.plot.legend_size))
            self.legend.draw_frame(self.plot.legend_border)
            self.legend.set_picker(legend_picker)
        else:
            self.legend=None
            self.axes.legend_=None
        if draw_canvas:
            self.canvas.draw()

    def gupdate(self, source=None):
        """Takes care of updating relevant parts"""

        self.redraw(sources=[source])

        for part in parts:
            if part == "all":
                self.draw()
            elif part == "legend":
                self.update_legend()
            elif part == "margins":
                self.update_margins()
            elif part == "rest":
                self.update()

    def update(self, limits=True, draw_canvas=True):
        """Updates everything but the Lines and legend"""
    #        if self.plot.shown:
        #self.draw()

        #if self.plot.legend_enable:
        #    self.update_legend()

        if self.plot.x_axis_label_enable:
            self.axes.set_xlabel(self.plot.x_axis_label)
        else:
            self.axes.set_xlabel("")

        if self.plot.y_axis_label_enable:
            self.axes.set_ylabel(self.plot.y_axis_label)
        else:
            self.axes.set_ylabel("")

        if self.plot.x_log_enable:
            self.axes.set_xscale("log")
        else:
            self.axes.set_xscale("linear")
        if self.plot.y_log_enable:
            self.axes.set_yscale("log")
        else:
            self.axes.set_yscale("linear")

        xaxis=self.axes.get_xaxis()
        xaxis.grid(self.plot.x_grid_enable, which="major")

        yaxis=self.axes.get_yaxis()
        yaxis.grid(self.plot.y_grid_enable, which="major")

        if limits:
            extr=self.plot.get_extremes()
            print "sxtr:", extr
            if len(extr) == 4:
                print "extr:", extr
                y_pad=(extr[3]-extr[2])*0.05
                #self.axes.set_xlim(extr[0], extr[1])
                #self.axes.set_ylim(extr[2]-y_pad, extr[3]+y_pad)


                if self.plot.xlim_enable:
                    print "xlim"
                    self.axes.set_xlim(self.plot.xlim_min, self.plot.xlim_max,
                                   emit=False)
                else:
                    self.axes.set_xlim(#map(lambda x: round_to_n(x, 5),
                                       extr[0], extr[1]) #)

                if self.plot.ylim_enable:
                    self.axes.set_ylim(self.plot.ylim_min, self.plot.ylim_max,
                                   emit=False)
                else:
                    y_limits=(extr[2], extr[3])#)#map(lambda y: round_to_n(y, 5),

                    y_pad=(y_limits[1]-y_limits[0])/20
                    self.axes.set_ylim(y_limits[0]-y_pad, y_limits[1]+y_pad)


        try:
            mpl_code=compile(self.plot.mpl_commands,'<string>','exec')
            eval(mpl_code, None, {"figure": self.figure,
                                  "axes": self.axes,
                                  "legend": self.legend,
                                  "s": self.plot.parent.source_list[:],
                                  "p": self.plot.parent.plt_combo.get_model_items().values(),
                                  "plot": self.plot})
        except:
            print "Invalid MPL code!"

        if draw_canvas:
            self.canvas.draw()

    def redraw(self, sources, draw_canvas=True):
        if sources != []:
            lines=[]
            for line in self.plot.lines:
                if line.source in sources and line not in lines:
                    lines.append(line)
            #legend=[]

            for line in lines:
                print("Redraw: "+line.source.name)
                source=line.source
                if source:
                    x_data, y_data=line.get_data()
                    #print x_data, y_data
                    # if source.norm_enable:
                        # print "NORMALIZE!"
                        # y_data=(source.y_data-source.y_data[source.norm_min_pt])/\
                                    # (source.y_data[source.norm_max_pt]-\
                                     # source.y_data[source.norm_min_pt])*\
                                    # (source.norm_max_y-source.norm_min_y)+source.norm_min_y
                    # if line.x_scale_enable:
                        # x_data=x_data*line.x_scale
                    # if line.y_scale_enable:
                        # y_data=y_data*line.y_scale
                    # if line.x_shift_enable:
                        # x_data=x_data+line.x_shift
                    # if line.y_shift_enable:
                        # y_data=y_data+line.y_shift
        #                if source.shift_enable:
        #                    x_data=source.x_data+source.shift

                    line.handle.set_data(x_data, y_data)
                    line.update_extremes()

                    line.handle.set_color(line.color)
                    line.handle.set_linewidth(line.width)
                    line.handle.set_marker(line.marker)

            try:
                s=self.plot.parent.source_list.get_selected_rows()[0]
            except:
                pass
            else:
                if self.show_cursors and s.norm_enable:
                    self.cursors.set_data(   #s.x_data, s.y_data)
                            [s.x_data[s.norm_min_pt],
                            s.x_data[s.norm_max_pt]],
                            [s.norm_min_y, s.norm_max_y])
                    self.cursors.set_marker('+')
                else:
                    self.cursors.set_marker("None")

            #print "getting axis limits"
            extr=self.plot.get_extremes()
            if not self.plot.xlim_enable:
                self.axes.set_xlim(extr[0], extr[1])
            if not self.plot.ylim_enable:
                y_pad=(extr[3]-extr[2])*0.05
                self.axes.set_ylim(extr[2]-y_pad, extr[3]+y_pad)

            #self.axes.redraw_in_frame() #????
            if draw_canvas:
                self.canvas.draw()

    def destroy_cb(self, widget):
        self.plot.shown=False
        #TreeDisplay.update_plot_state()
        #self.pos=self.window.get_position()
        #self.size=self.window.get_size()
        #print self.pos
        self.window.destroy()
        #self.plot.shown=False
        self.plot.parent.shown.update(False)
        #self.plot.parent.shown=False
        #self.plot.update_plot_info()

    #callbacks
    def rectangle_cb(self, event1, event2):
        print event1.xdata, event1.ydata, event2.xdata, event2.ydata
        self.plot.x_lim_min=event1.xdata
        self.plot.x_lim_max=event2.xdata
        self.plot.y_lim_min=event1.ydata
        self.plot.y_lim_max=event2.ydata
        self.axes.set_xlim(min(event1.xdata,event2.xdata), max(event1.xdata,event2.xdata))
        self.axes.set_ylim(min(event1.ydata,event2.ydata), max(event1.ydata,event2.ydata))
        self.canvas.draw()

    def button_up_cb(self,event):
        self.plot.xlim_min, self.plot.xlim_max=self.axes.get_xlim()
        self.plot.ylim_min, self.plot.ylim_max=self.axes.get_ylim()

        if not self.plot.xlim_enable:
            self.plot.parent.xlim_min.update(self.plot.xlim_min)
            self.plot.parent.xlim_max.update(self.plot.xlim_max)

        if not self.plot.ylim_enable:
            self.plot.parent.ylim_min.update(self.plot.ylim_min)
            self.plot.parent.ylim_max.update(self.plot.ylim_max)


    def xlim_cb(self,event):
        #print "xlim changed to: "+str(self.axes.get_xlim())
        self.plot.xlim_min, self.plot.xlim_max=self.axes.get_xlim()
        if not self.plot.xlim_enable:
            self.plot.parent.xlim_min.update(self.plot.xlim_min)
            self.plot.parent.xlim_max.update(self.plot.xlim_max)
        #pass

    def ylim_cb(self,event):
        #print "ylim changed to: "+str(self.axes.get_ylim())
        self.plot.ylim_min, self.plot.ylim_max=self.axes.get_ylim()
        if not self.plot.ylim_enable:
            self.plot.parent.ylim_min.update(self.plot.ylim_min)
            self.plot.parent.ylim_max.update(self.plot.ylim_max)
        #pass

    def pick_cb (self, event ) :
        print event.artist
        if isinstance(event.artist, Line2D):
            print event.artist.parent.label
            xdata=event.artist.get_xdata()
            ydata=event.artist.get_ydata()
            print event.ind[0]
            print xdata[event.ind[0]], ydata[event.ind[0]]
            axes_h=self.axes.get_ylim()
            print axes_h

            self.plot.parent.plot_notebook.set_current_page(0)
            self.plot.parent.lines_list.select(event.artist.parent)

    #            arrow_h=0.1*(axes_h[1]-axes_h[0])
    #            self.axes.arrow(xdata[event.ind[0]],ydata[event.ind[0]],0,arrow_h,label="A", visible=True)
    #            self.canvas.draw()
            #self.axes.arrow(0.5,0.5,0.1,0.1)

        if isinstance(event.artist, Legend):
            print "legend clicked"
            self.plot.parent.plot_notebook.set_current_page(2)

        else:
            print event
