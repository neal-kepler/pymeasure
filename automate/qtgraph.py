#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Classes for using PyQtGraph
#
# automate Python package
# Authors: Colin Jermain, Graham Rowlands
# Copyright: 2014 Cornell University
#
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
from automate.experiment import Results
from PyQt4.QtCore import pyqtSignal, QObject
import pyqtgraph as pg
import numpy as np

class ResultsCurve(pg.PlotDataItem):
    """ Creates a curve loaded dynamically from a file through the Results
    object and supports error bars. The data can be forced to fully reload
    on each update, useful for cases when the data is changing across the full
    file instead of just appending.
    """
    
    def __init__(self, results, x, y, xerr=None, yerr=None, force_reload=False, **kwargs):
        pg.PlotDataItem.__init__(self, **kwargs)
        self.results = results
        self.x, self.y = x, y
        self.force_reload = force_reload
        if xerr or yerr:
            self._errorBars = pg.ErrorBarItem(pen=kwargs.get('pen', None))
            self.xerr, self.yerr = xerr, yerr
    
    def update(self):
        """Updates the data by polling the results"""
        
        if self.force_reload:
            self.results.reload()
        data = self.results.data # get the current snapshot    
        
        # Set x-y data
        self.setData(data[self.x], data[self.y])
        
        # Set error bars if enabled at construction
        if hasattr(self, '_errorBars'):
            self._errorBars.setOpts(
                        x=data[self.x],
                        y=data[self.y],
                        top=data[self.yerr], 
                        bottom=data[self.yerr],
                        left=data[self.xerr],
                        right=data[self.yerr],
                        beam=max(data[self.xerr], data[self.yerr])
                    )

class BufferCurve(pg.PlotDataItem):
    """ Creates a curve based on a predefined buffer size and allows
    data to be added dynamically, in additon to supporting error bars
    """
    
    data_updated = pyqtSignal()
    
    def __init__(self, errors=False, **kwargs):
        pg.PlotDataItem.__init__(self, **kwargs)
        if errors:
            self._errorBars = pg.ErrorBarItem(pen=kwargs.get('pen', None))
        self._buffer = None
        
    def prepare(self, size, dtype=np.float32):
        """ Prepares the buffer based on its size, data type """
        if hasattr(self, '_errorBars'):
            self._buffer = np.empty((size,4), dtype=dtype)
        else:
            self._buffer = np.empty((size,2), dtype=dtype)
        self._ptr = 0
        
    def append(self, x, y, xError=None, yError=None):
        """ Appends data to the curve with optional errors """
        if self._buffer is None:
            raise Exception("BufferCurve buffer must be prepared")
        if len(self._buffer) <= self._ptr:
            raise Exception("BufferCurve overflow")
            
        # Set x-y data
        self._buffer[self._ptr,:2] = [x, y]
        self.setData(self._buffer[:self._ptr,:2])
        
        # Set error bars if enabled at construction
        if hasattr(self, '_errorBars'):
            self._buffer[self._ptr,2:] = [xError, yError]
            self._errorBars.setOpts(
                        x=self._buffer[:self._ptr,0],
                        y=self._buffer[:self._ptr,1],
                        top=self._buffer[:self._ptr,3], 
                        bottom=self._buffer[:self._ptr,3],
                        left=self._buffer[:self._ptr,2],
                        right=self._buffer[:self._ptr,2],
                        beam=np.max(self._buffer[:self._ptr,2:])
                    )
                    
        self._ptr += 1
        self.data_updated.emit()
        
class Crosshairs(QObject):
    """ Attaches crosshairs to the a plot and provides a signal with the
    x and y graph coordinates
    """
    
    coordinates = pyqtSignal(float, float)
    
    def __init__(self, plot, pen=None):
        """ Initiates the crosshars onto a plot given the pen style.
        
        Example pen:
        pen=pg.mkPen(color='#AAAAAA', style=QtCore.Qt.DashLine)
        """      
        QObject.__init__(self)
        self.vertical = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.horizontal = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        plot.addItem(self.vertical, ignoreBounds=True)
        plot.addItem(self.horizontal, ignoreBounds=True)
        
        self.position = None
        self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, 
                                    slot=self.mouseMoved)
        self.plot = plot
    
    def hide(self):
        self.vertical.hide()
        self.horizontal.hide()
        
    def show(self):
        self.vertical.show()
        self.horizontal.show()
        
    def update(self):
        """ Updates the mouse position based on the data in the plot. For 
        dynamic plots, this is called each time the data changes to ensure
        the x and y values correspond to those on the display.
        """
        if self.position is not None:
            mousePoint = self.plot.vb.mapSceneToView(self.position)
            self.coordinates.emit(mousePoint.x(), mousePoint.y())
            self.vertical.setPos(mousePoint.x())
            self.horizontal.setPos(mousePoint.y())
            
    def mouseMoved(self, event=None):
        """ Updates the mouse position upon mouse movement """
        if event is not None:
            self.position = event[0]
            self.update()
        else:
            raise Exception("Mouse location not known")
        