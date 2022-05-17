import funzioni_plot
import sys,os


s4_read=funzioni_plot.ReadRTKLIBoutstats('{}/files/example.pos.stat'.format(os.path.dirname(os.path.realpath(__file__))),'S4')

funzioni_plot.plotMDP_MS(s4_read,1,'S4','Example plot of S4 quantity')