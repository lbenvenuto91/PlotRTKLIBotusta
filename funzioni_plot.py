from cProfile import label
import sys,os
import numpy as np
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def weeksecondstoutc(gpsweek,gpsseconds,leapseconds=0):
    '''
    Funzione per convertire la settimana GPS e il TOW in un oggetto datetime

    leapseconds?

    '''
    #import datetime, calendar
    datetimeformat = "%Y-%m-%d %H:%M:%S.%f"
    epoch = datetime.strptime("1980-01-06 00:00:00.00",datetimeformat)
    elapsed = timedelta(days=(gpsweek*7),seconds=(gpsseconds+leapseconds))
    #print(datetime.strftime(epoch + elapsed,datetimeformat))
    return(epoch + elapsed)


def str2Date(stringa):
    #print(stringa)
    ydoysec=stringa.split(':')
    #print(ydoysec)
    ydoy=('{}:{}'.format(ydoysec[0],ydoysec[1]))
    istante=datetime.strptime(ydoy, '%y:%j')
    istante += timedelta(seconds=int(ydoysec[2]))
    return istante


def ReadCSRSoutput(filein,site):
    '''
    Funzione per leggere i file .pos generati come output dal sw CSRS   
    Chiede in input il file desiderato
    Restituisce una lista di tuple del tipo [(data1,output1), (data2,output2).....(datan,outputn)]
    data è un datetime object, output è un float
    '''
    if filein.endswith('.pos'):
        with open (filein,'r') as elabfile:
            read=elabfile.readlines()
            header=[i.split() for i in read if i.split()[0].startswith('DIR')]
            #print(header)
            for i,j in zip(header[0],range(len(header[0]))):
                print (i,'-->',j)
            index=int(input('cosa graficare? -->'))
            body_temp=[[b.split()[4]+' '+b.split()[5],b.split()[index]] for b in read if b.split()[0].startswith('FWD')]
            return [(datetime.strptime(i[0],'%Y-%m-%d %H:%M:%S.%f'),float(i[1])) for i in body_temp]
    elif filein.endswith('.tro'):
        with open (filein,'r') as elabfile:
            read=elabfile.readlines()
            header=[i.split() for i in read if i.split()[0].startswith('*SITE') and i.split()[-1].endswith('STDDEV')]
            #site='TORI'
            for i,j in zip(header[0],range(len(header[0]))):
                print (i,'-->',j)
            index=int(input('cosa graficare? -->'))
            body_temp=[[b.split()[1],b.split()[index]] for b in read if b.split()[0].startswith(site)]
            #print(body_temp)
            body_temp=body_temp[1:]

            return [(str2Date(i[0]),float(i[1])/1000) for i in body_temp]


def ReadRTKLIBoutstats(filein,typestats):
    '''
    Funzione per leggere i file .pos.stats generati come output dal sw RTKLIB  
    Chiede in input:
    - file desiderato
    - stats da leggeere = ['ION','POS','CLK','TROP','MDP']
    
    Restituisce una lista di tuple del tipo [(data1,output1), (data2,output2).....(datan,outputn)]
    data è un datetime object, output è un float
    '''
    with open (filein,'r') as elabfile:
        read=elabfile.readlines()

    if typestats=='TROP':
        return[(weeksecondstoutc(int(i.split(sep=',')[1]),float(i.split(sep=',')[2])),float(i.split(sep=',')[5])) for i in read if i.split(sep=',')[0].startswith('${}'.format(typestats))]
    elif typestats=='POS':
        return[(weeksecondstoutc(int(i.split(sep=',')[1]),float(i.split(sep=',')[2])),float(i.split(sep=',')[4]),float(i.split(sep=',')[5]),float(i.split(sep=',')[6]),int(i.split(sep=',')[3])) for i in read if i.split(sep=',')[0].startswith('${}'.format(typestats))]
    elif typestats=='MDP':
        #$MDP,gpsweek,tow,satid,freq,mdp
        tmp=[(weeksecondstoutc(int(i.split(sep=',')[1]),float(i.split(sep=',')[2])),i.split(sep=',')[3],int(i.split(sep=',')[4]),float(i.split(sep=',')[5])) for i in read if i.split(sep=',')[0].startswith('${}'.format(typestats))]
        return[i for i in tmp if i[3]!=999.99] #elimino valori nulli
    elif typestats=='S4':
        #$S4,gpsweek,tow,satid,freq,s4
        tmp=[(weeksecondstoutc(int(i.split(sep=',')[1]),float(i.split(sep=',')[2])),i.split(sep=',')[3],int(i.split(sep=',')[4]),float(i.split(sep=',')[5])) for i in read if i.split(sep=',')[0].startswith('${}'.format(typestats))]
        return[i for i in tmp if i[3]!=999.990] #e



def convertSinexTimeFormat(str_date):
    '''
    funzione per convertire una strina di testo formato yy:doy:sssss in un datetime.object
    '''
    ydoy=str_date[0:-6]
    secondi=int(str_date.split(':')[2])
    try:
        a=datetime.strptime(ydoy, '%y:%j')
        return a+timedelta(seconds=secondi)
    except ValueError as ve:
        print('ValueError Raised:', ve)
        return

def SinexParser(sinex_file):
    '''
    Funzione per leggere un file in formato SINEX con i dati di ZTD
    Non vengono lette le coordinate delle stazioni nell'header

    La funzione restituisce un dizionario con:
        -chiavi: nomi delle stazioni
        -valori: lista di tuple del tipo [(datetime1,ztd1)... (datetimen,ztdn)]

    '''
    sfile = [line.strip('\n').split() for line in open(sinex_file).readlines()]
    #creo un array più piccolo con solo le soluzioni: dalla riga +TROP/SOLUTION alla riga -TROP/SOLUTION
    #print(sfile.index(['+TROP/SOLUTION']))
    solfile=sfile[sfile.index(['+TROP/SOLUTION'])+2:sfile.index(['-TROP/SOLUTION'])] # +2 perchè sennò avrei anche le rige +TROP/SOLUTION e *SITE ___EPOCH___ TROTOT STDDEV TGNTOT STDDEV TGETOT STDDEV
    sol_dict={}

    for i in solfile:
        ztd=float(i[2])
        time_stamp=convertSinexTimeFormat(i[1])
        if i[0] in sol_dict:
            sol_dict[i[0]].append((time_stamp,ztd*0.001)) #ztd in metri
        else:
            sol_dict[i[0]]=[(time_stamp,ztd*0.001)] #ztd in metri
        
    return sol_dict

        


def plotMDP_SS(data,satellite,frequenza=1,ytitle='MDP',title="",visualize=True):
    '''
    funzione per plottare ZTD per una singolo satellite
    chiede in input:
    - una lista di dati che si ottiene con la funzione readData
    - una stringa col satellite da plottare
    - un int relativo alla frequenza da plottare
    - un titolo per l'asse y. Di default è ZTD [m]
    - titolo da dare al grafico. Di default è none
    '''
    asse_x=[data[i][0] for i in range(len(data)) if data[i][1]==satellite and data[i][2]==frequenza]
    asse_y_read=[data[i][3] for i in range(len(data)) if data[i][1]==satellite and data[i][2]==frequenza]
    asse_y=[]
    for i in asse_y_read:
        if i==0.0:
            asse_y.append(np.nan)
        else:
            asse_y.append(i)

    soglie=calcolasoglia(asse_x,asse_y,30)
    asse_xs=[soglie[i][0] for i in range(len(soglie))]
    asse_ysu=[soglie[i][1] for i in range(len(soglie))]
    asse_ysd=[soglie[i][2] for i in range(len(soglie))]
    plt.figure(figsize=(8,6))
    plt.plot(asse_x,asse_y)
    #plt.xticks(rotation=45)
    plt.xlabel('UTC time',fontsize=18)
    plt.ylabel(ytitle,fontsize=18)

    plt.plot(asse_xs,asse_ysu,label='mdp upper threshold')

    plt.plot(asse_xs,asse_ysd,label='mdp lower threshold')
    
    plt.title(title,fontsize=20,fontweight="bold")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.grid(True)
    plt.legend(loc='lower left')
    if visualize:
        plt.show()
    else:
        plt.close()


def plotMDP_MS(data,frequenza=1,ytitle='MDP',title="",visualize=True):
    '''
    funzione per plottare ZTD per tutti i satelliti osservati
    chiede in input:
    - una lista di dati che si ottiene con la funzione readData
    - un int relativo alla frequenza da plottare
    - un titolo per l'asse y. Di default è ZTD [m]
    - titolo da dare al grafico. Di default è none
    '''
    satelliti=[]

    for i in data:
        if i[1] not in satelliti:
            satelliti.append(i[1])
    plt.figure(figsize=(8,6))
    for satellite in satelliti:

        asse_x=[data[i][0] for i in range(len(data)) if data[i][1]==satellite and data[i][2]==frequenza]
        asse_y_read=[data[i][3] for i in range(len(data)) if data[i][1]==satellite and data[i][2]==frequenza]
        asse_y=[]
        for i in asse_y_read:
            if i==0.0:
                asse_y.append(np.nan)
            else:
                asse_y.append(i)
        plt.plot(asse_x,asse_y,'.',label=satellite)
    #plt.xticks(rotation=45)
    plt.xlabel('UTC time',fontsize=18)
    plt.ylabel(ytitle,fontsize=18)
    plt.title(title,fontsize=20,fontweight="bold")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    #plt.ylim(-30,30)
    plt.grid(True)
    plt.legend(loc='best',ncol=10)
    if visualize:
        plt.show()
    else:
        plt.close()



def plotZTD_MS(data,names,title=""):
    '''
    funzione per plottare ZTD per più stazioni
    chiede in input:
    - una un array di liste di dati che si ottiengono con la funzione readData
    - titolo da dare al grafico. Di default è none
    '''
    minimi=[]
    massimi=[]
    for i,k in zip(data,names):
        asse_x=[i[j][0] for j in range(len(i))]
        asse_y=[i[j][1] for j in range(len(i))]
        minimi.append(min(asse_y))
        massimi.append(max(asse_y))
        plt.plot(asse_x,asse_y,".",label=k)
    #plt.xticks(rotation=45)
    plt.xlabel('UTC time')
    plt.ylabel('ZTD [m]')
    plt.yticks(np.arange(round(min(minimi),3), round(max(massimi),3), step=0.001))
    plt.title(title)
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.legend()
    plt.show()
    
def cfrS4(dati1,dati2):
    '''
    funzione che prende in input due liste di dati e fa la differenza dei valori di S4
    Prima di fare la differenza viene controllato che l'istante temporale sia lo stesso
    
    ritorna una lista con i S4 residuals
    '''
    dati2_dict={}
    cfr_data=[]
    for i in dati2:
        dati2_dict[i[0]]=i[1]
    #print(dati2_dict)
    for j in dati1:
        if j[0] in dati2_dict.keys():
            #print(j[0],j[1],dati2_dict[j[0]])
            cfr_data.append((j[0],j[1]-dati2_dict[j[0]]))
        else:
            continue
    return (cfr_data)



def plotS4_SS(data,satellite,frequenza=1,ytitle='S4',title="",visualize=True):
    '''
    funzione per plottare ZTD per una singolo satellite
    chiede in input:
    - una lista di dati che si ottiene con la funzione readData
    - una stringa col satellite da plottare
    - un int relativo alla frequenza da plottare
    - un titolo per l'asse y. Di default è ZTD [m]
    - titolo da dare al grafico. Di default è none
    '''
    asse_x=[data[i][0] for i in range(len(data)) if data[i][1]==satellite and data[i][2]==frequenza]
    asse_y_read=[data[i][3] for i in range(len(data)) if data[i][1]==satellite and data[i][2]==frequenza]
    asse_y=[]
    for i in asse_y_read:
        if i==0.0:
            asse_y.append(np.nan)
        else:
            asse_y.append(i)

    return [asse_x,asse_y]
    plt.figure()
    plt.plot(asse_x,asse_y,'*')
    #plt.xticks(rotation=45)
    plt.xlabel('UTC time',fontsize=18)
    plt.ylabel(ytitle,fontsize=18)
    plt.ylim(0,0.7)
    plt.title(title,fontsize=20,fontweight="bold")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.grid(True)
    plt.legend(loc='best')
    if visualize:
        plt.show()
    else:
        plt.close()







def calcolasoglia(date,mdp,epoche):
    s=0
    tmp=[]
    soglie=[]
    for i,j in zip (date,mdp):
        if s < epoche:
            print(i,j, "no soglia")
            tmp.append(j)
            s+=1
        else:

            #print(i,j,np.nanmean(tmp),np.std(tmp))
            soglie.append((i,np.nanmean(tmp)+3*np.nanstd(tmp),np.nanmean(tmp)-3*np.nanstd(tmp)))
            tmp=tmp[1:]
            tmp.append(j)
            s+=1
    return(soglie)




def pltHist(lstdati,larghezza_classe,titolo,nome_staz):
    '''
    Funzione che prende in input una serie di dati e:
        - suddivide la serie di dati in n classi di grandezza specificata dall'utente
        - calcola il numero di samples per ogni classe, stampandolo a video
        - calcola media, varianza e deviazione standard della serie di dati in input
        - plotta un istogramma con le statistiche calcolate   
    '''
    x=[lstdati[i][1] for i in range(len(lstdati))]
    print(max(x))
    istogramma=np.histogram(x,bins=np.arange(min(x), max(x), larghezza_classe),density=False)
    
    #istogramma=np.histogram(x,bins='doane',density=False)#--> documentarsi meglio sulle varie stringhe di bins
    #con density=False la funzione np.histogram resituisce il numero di samples per ogni classe
    print('\n########### STAZIONE {} ###########\n'.format(nome_staz))
    print('larghezza classe = {}m\nnumero di classi = {}'.format(larghezza_classe,len(istogramma[0])))
    i=0
    while i<(len(istogramma[0])):
        print('classe {}: centro= {}m, numero di samples= {}'.format(i+1,round(np.mean([istogramma[1][i],istogramma[1][i+1]]),4),istogramma[0][i]))
        i+=1

    #statistiche sulla serie completa
    
    med=round(np.mean(np.array(x)),5)
    var=round(np.var(np.array(x)),5)
    std=round(np.std(np.array(x)),5)
    
    #plot istogramma
    plt.hist(x, bins=np.arange(min(x), max(x), larghezza_classe), label=('media= {}\nvar= {}\nstd={}'.format(med,var,std)))
    plt.title(titolo)
    plt.legend()
    #plt.grid(True)
    plt.figure()
    plt.hist(x, bins=np.arange(min(x), max(x), larghezza_classe),density=True,cumulative=True, histtype='step',linewidth=2)
    plt.grid(True)
    plt.title('Cumulative function')
    plt.xlabel('ZTD residuals [m]')
    plt.show()

