import sys, copy, types
from kiwi.model import Model
from fileutils import load_data
import numpy
from numpy import array, transpose, arange, min, max
import re
import physcon as pc
import specutils as su
import traceback as tb

class SourceError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class TreeItem(Model):
    id=-1
    name="test"
    datafile=None
    toggle=False
    folder=False

class Folder(TreeItem):
    def __init__(self, name):
        self.name=name
        self.folder=True
        self.children=[]

class GeneratedColumn:
    def __init__(self, source=None, id=0, name=None, expr="", data=[]):
        self.source=source
        self.id=id
        if name is None:
            self.name="g"+str(id)
        else:
            self.name=name
        self.expr=expr
        self.data=data
        self.enabled=False

    def make_col_dict(self, cont):
        for i, col in enumerate(self.source.data):
            cont["c"+str(i)]=col
        for col in self.source.gen_cols:
            print col.name, col.enabled
            if col.id != self.id and col.enabled:
                cont["g"+str(col.id)]=col.data
        return cont

    def update_data(self, sources):
        c_re=re.compile("c\d+")
        s_re=re.compile("s\d+")
        c_ids=map(lambda x: int(x[1:]),c_re.findall(self.expr))
        s_ids=map(lambda x: int(x[1:]),s_re.findall(self.expr))
        context=self.source.make_src_dict(sources, [], [], s_ids)
        context["x"]=self.source.data[self.source.x_col]
        context["y"]=self.source.data[self.source.y_col]
        context["s"]=self.source.data
        context=self.make_col_dict(context)
        context["s"]=self.source.data
        context["pc"]=pc
        context["su"]=su

        print context.keys()

        try:
            self.data=eval(self.expr, numpy.__dict__, context)
            self.enabled=True
            return True
        except:
            print "Illegal column expression: ", self.expr
            self.enabled=False
            return False

class Subject:

    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    def notify(self):
        plots=set([])
        for observer in self._observers:
            plots.add(observer.redraw())
        return plots



class Source(Subject):
    id=-1

    def __init__(self, id=0, datafile=None, name="", data=None, x_col=0, y_col=1,
                 folder=False,
                 x_expr="x", x_expr_enable=False, y_expr="y",  y_expr_enable=False,
                 norm_enable=False, norm_max_pt=0, norm_max_y=0, norm_min_pt=0, norm_min_y=0,
                 scale_enable=False, scale=1, shift_enable=False, shift=0, comment=""):

        Subject.__init__(self)

        self.folder=folder
        self.transpose=False

        if data is not None:
            self.data=data
        elif datafile:
            try:
                self.data=load_data(datafile)
            except:
                raise SourceError(1)
                return None
        else:
            x_data=array([])
            y_data=array([])
            self.data=array([x_data, y_data])

        # if self.data.shape[0] > self.data.shape[1]:
            # print "Transposing short data"
            # self.transpose=True
            # self.data=transpose(self.data)

        if len(self.data)==1:
            print "One column data; generating X column..."
            self.x_data=arange(len(self.data[0]))
            self.y_data=self.data[0]
        else:
            self.x_data=self.data[x_col]
            self.y_data=self.data[y_col]


        self.id=id

        self.file=datafile
        if name=="":
            if datafile is None:
                self.name="Source"+str(self.id)
            else:
                self.name=datafile.split("/")[-1].split(".")[0].replace("_"," ")
        else:
            self.name=name

    #        self.plots=[]

        if not folder:
            self.x_col=x_col
            self.y_col=y_col

            self.y_expr=y_expr
            self.y_expr_enable=y_expr_enable
            if x_expr is "x":
                if len(self.data) != 1:
                    self.x_expr=x_expr
                    self.x_expr_enable=x_expr_enable
                else:
                    self.x_expr="arange("+str(len(self.data[0]))+")"
                    self.x_expr_enable=True
            else:
                self.x_expr=x_expr
                self.x_expr_enable=x_expr_enable

            self.norm_enable=False
            if len(self.y_data)>0:
                #self.norm_min_pt=self.y_data.argmin()
                #self.norm_max_pt=self.y_data.argmax()
                self.norm_min_pt=0
                self.norm_max_pt=len(self.y_data)-1
            else:
                self.norm_min_pt=0
                self.norm_max_pt=0
            self.norm_min_y=0.0
            self.norm_max_y=1.0

            self.scale_enable=False
            self.scale=1.0
            self.shift_enable=False
            self.shift=0.0

            self.gen_col_id = len(self.data)
            self.gen_cols = []

        self.comment=comment
        self.toggle=False

    def __getstate__(self):
        d=copy.copy(self.__dict__)
        d["_observers"]=[]
        for item in d:
            if type(d[item])==types.FunctionType:
                del(d[item])
        return d

    def __setstate__(self, newstate):
       for item in newstate.keys():
           self.__dict__[item]=newstate[item]

    def next_gen_col_id(self):
        self.gen_col_id+=1
        return self.gen_col_id-1

    def load_data(self):
        self.data=load_data(self.file)

    def make_src_dict(self, sources, x_ids, y_ids, s_ids):
        dict={}
        for src in sources:
            if src.id in s_ids:
                dict["s"+str(src.id)]=src.data
            if src.id in x_ids:
                dict["x"+str(src.id)]=src.x_data
            if src.id in y_ids:
                dict["y"+str(src.id)]=src.y_data
        return dict

    def update_x_data(self, sources):
        if self.x_expr_enable:
            x_re=re.compile("x\d+")
            y_re=re.compile("y\d+")
            s_re=re.compile("s\d+")
            x_ids=map(lambda x: int(x[1:]),x_re.findall(self.x_expr))
            y_ids=map(lambda x: int(x[1:]),y_re.findall(self.x_expr))
            s_ids=map(lambda x: int(x[1:]),s_re.findall(self.x_expr))
            print "x ids: ", x_ids
            print "y ids: ", y_ids
            print "s ids: ", s_ids

            context=self.make_src_dict(sources, x_ids, y_ids, s_ids)
            context["x"]=self.data[self.x_col]
            context["y"]=self.data[self.y_col]
            context["s"]=self.data
            context["pc"]=pc
            context["su"]=su

            #print context.keys()

            try:
                self.x_data=eval(self.x_expr, numpy.__dict__, context)

            except:
                print "Illegal X expression: ", self.x_expr
                print tb.format_list(tb.extract_tb(sys.exc_info()[2]))
                self.x_data=self.data[self.x_col]
                return False
            else:
                return True
        else:
            if self.data != []:
                self.x_data=self.data[self.x_col]
            elif self.y_data != []:
                self.x_data=arange(0,len(self.y_data))
            return True

    def update_y_data(self, sources):
        if self.y_expr_enable:
            x_re=re.compile("x\d+")
            y_re=re.compile("y\d+")
            s_re=re.compile("s\d+")
            x_ids=map(lambda x: int(x[1:]),x_re.findall(self.y_expr))
            y_ids=map(lambda x: int(x[1:]),y_re.findall(self.y_expr))
            s_ids=map(lambda x: int(x[1:]),s_re.findall(self.y_expr))
            context=self.make_src_dict(sources, x_ids, y_ids, s_ids)
            context["x"]=self.x_data
            context["y"]=self.data[self.y_col]
            context["s"]=self.data
            context["pc"]=pc
            context["su"]=su

            print context.keys()
            try:
                self.y_data=eval(self.y_expr, numpy.__dict__, context)
            except:
                print "Illegal Y  expression: ", self.y_expr
                self.y_data=self.data[self.y_col]
                return False
            else:
                return True
        else:
            self.y_data=self.data[self.y_col]
            return True
