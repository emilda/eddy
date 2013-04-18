import ast
import copy
import constants as c
import datetime
import numpy
import time
import qcts
import qcutils
import logging

log = logging.getLogger('qc.ck')

def do_7500check(cf,ds):
    '''Rejects data values for series specified in LI75List for times when the Diag_7500
       flag is non-zero.  If the Diag_7500 flag is not present in the data structure passed
       to this routine, it is constructed from the QC flags of the series specified in
       LI75Lisat.  Additional checks are done for AGC_7500 (the LI-7500 AGC value),
       Ah_7500_Sd (standard deviation of absolute humidity) and Cc_7500_Sd (standard
       deviation of CO2 concentration).'''
    log.info(' Doing the 7500 check')
    LI75List = ['Ah_7500_Av','Cc_7500_Av','AhAh','CcCc',
                'UzA','UxA','UyA','UzC','UxC','UyC']
    if 'Diag_7500' not in cf['Variables'].keys():
        ds.series[unicode('Diag_7500')] = {}
        nRecs = numpy.size(ds.series['xlDateTime']['Data'])
        ds.series['Diag_7500']['Flag'] = numpy.zeros(nRecs,dtype=int)
        for ThisOne in ['Ah_7500_Av','Cc_7500_Av']:
            if ThisOne in ds.series.keys():
                index = numpy.where(ds.series[ThisOne]['Flag']!=0)[0]
                log.info(' do_7500check: ', ThisOne, ' rejected ',len(index))
                ds.series['Diag_7500']['Flag'] = ds.series['Diag_7500']['Flag'] + ds.series[ThisOne]['Flag']
    index = numpy.where(ds.series['Diag_7500']['Flag']!=0)
    log.info('  7500Check: Diag_7500 ' + str(numpy.size(index)))
    for ThisOne in ['AGC_7500','Ah_7500_Sd','Cc_7500_Sd','AhAh','CcCc']:
        if ThisOne in ds.series.keys():
            index = numpy.where(ds.series[ThisOne]['Flag']!=0)
            log.info('  7500Check: ' + ThisOne + ' ' + str(numpy.size(index)))
            ds.series['Diag_7500']['Flag'] = ds.series['Diag_7500']['Flag'] + ds.series[ThisOne]['Flag']
    index = numpy.where((ds.series['Diag_7500']['Flag']!=0))
    log.info('  7500Check: Total ' + str(numpy.size(index)))
    for ThisOne in LI75List:
        if ThisOne in ds.series.keys():
            ds.series[ThisOne]['Data'][index] = numpy.float64(-9999)
            ds.series[ThisOne]['Flag'][index] = 4
        else:
            log.error('  qcck.do_7500check: series '+str(ThisOne)+' in LI75List not found in ds.series')

def do_Ah7500check(cf,ds,Fcvar='Fc'):
    '''Cleans up Ah_7500_Av based upon Fc_wpl gaps to for QA check on Ah_7500_Av v Ah_HMP.'''
    log.info(' Doing the Ah_7500 check')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='AhcheckFc'):
        Fcvar = cf['FunctionArgs']['AhcheckFc']
    
    # index1  Index of bad Ah_7500_Av observations
    index1 = numpy.where((ds.series['Ah_7500_Av']['Flag']!=0) & (ds.series['Ah_7500_Av']['Flag']!=10))
    
    # index2  Index of bad Fc observations
    index2 = numpy.where((ds.series[Fcvar]['Flag']!=0) & (ds.series[Fcvar]['Flag']!=10))
    
    ds.series['Ah_7500_Av']['Data'][index2] = numpy.float64(-9999)
    ds.series['Ah_7500_Av']['Flag'][index2] = ds.series[Fcvar]['Flag'][index2]
    ds.series['Ah_7500_Av']['Flag'][index1] = ds.series['Ah_7500_Av']['Flag'][index1]

def do_CSATcheck(cf,ds):
    '''Rejects data values for series specified in CSATList for times when the Diag_CSAT
       flag is non-zero.  If the Diag_CSAT flag is not present in the data structure passed
       to this routine, it is constructed from the QC flags of the series specified in
       CSATList.'''
    log.info(' Doing the CSAT check')
    if 'Wd_CSAT_Compass' in ds.series.keys():
        Wd = 'Wd_CSAT_Compass'
    else:
        Wd = 'Wd_CSAT'
    CSATList = ['Ux','Uy','Uz','Ws_CSAT',Wd,'Tv_CSAT',
                'UzT','UxT','UyT','UzA','UxA','UyA','UzC','UxC','UyC',
                'UxUz','UyUz','UxUy','UxUx','UyUy']
    if 'Diag_CSAT' not in cf['Variables'].keys():
        ds.series['Diag_CSAT']= {}
        nRecs = numpy.size(ds.series['xlDateTime']['Data'])
        ds.series['Diag_CSAT']['Flag'] = numpy.zeros(nRecs,dtype=int)
        for ThisOne in ['Ux','Uy','Uz','Tv_CSAT']:
            if ThisOne in ds.series.keys():
                index = numpy.where(ds.series[ThisOne]['Flag']!=0)[0]
                log.info(' do_CSATcheck: ', ThisOne, ' rejected ',len(index))
                ds.series['Diag_CSAT']['Flag'] = ds.series['Diag_CSAT']['Flag'] + ds.series[ThisOne]['Flag']
    index = numpy.where(ds.series['Diag_CSAT']['Flag']!=0)
    log.info('  CSATCheck: Diag_CSAT ' + str(numpy.size(index)))
    for ThisOne in CSATList:
        if ThisOne in ds.series.keys():
            ds.series[ThisOne]['Data'][index] = numpy.float64(-9999)
            ds.series[ThisOne]['Flag'][index] = 3
        else:
            log.error('  qcck.do_CSATcheck: series '+str(ThisOne)+' in CSATList not found in ds.series')

def do_diurnalcheck(cf,ds,ThisOne,code=5):
    dt = float(ds.globalattributes['time_step'])
    n = int((60./dt) + 0.5)             #Number of timesteps per hour
    nInts = int((1440.0/dt)+0.5)        #Number of timesteps per day
    Av = numpy.array([-9999]*nInts,dtype=numpy.float64)
    Sd = numpy.array([-9999]*nInts,dtype=numpy.float64)
    if qcutils.incf(cf,ThisOne) and qcutils.haskey(cf,ThisOne,'DiurnalCheck'):
        if 'NumSd' in cf['Variables'][ThisOne]['DiurnalCheck'].keys():
            NSd = numpy.array(eval(cf['Variables'][ThisOne]['DiurnalCheck']['NumSd']),dtype=float)
            for m in range(1,13):
                mindex = numpy.where(ds.series['Month']['Data']==m)[0]
                if len(mindex)!=0:
                    lHdh = ds.series['Hdh']['Data'][mindex]
                    l2ds = ds.series[ThisOne]['Data'][mindex]
                    for i in range(nInts):
                        li = numpy.where(abs(lHdh-(float(i)/float(n))<c.eps)&(l2ds!=float(-9999)))
                        if numpy.size(li)!=0:
                            Av[i] = numpy.mean(l2ds[li])
                            Sd[i] = numpy.std(l2ds[li])
                        else:
                            Av[i] = float(-9999)
                            Sd[i] = float(-9999)
                    Lwr = Av - NSd[m-1]*Sd
                    Upr = Av + NSd[m-1]*Sd
                    hindex = numpy.array(n*lHdh,int)
                    index = numpy.where(((l2ds!=float(-9999))&(l2ds<Lwr[hindex]))|
                                        ((l2ds!=float(-9999))&(l2ds>Upr[hindex])))[0] + mindex[0]
                    ds.series[ThisOne]['Data'][index] = float(-9999)
                    ds.series[ThisOne]['Flag'][index] = code
            ds.series[ThisOne]['Attr']['DiurnalCheck_NumSd'] = cf['Variables'][ThisOne]['DiurnalCheck']['NumSd']

def do_excludedates(cf,ds,ThisOne):
    if ThisOne in cf['Variables'].keys():
        if 'ExcludeDates' in cf['Variables'][ThisOne].keys():
            ldt = ds.series['DateTime']['Data']
            ExcludeList = cf['Variables'][ThisOne]['ExcludeDates'].keys()
            NumExclude = len(ExcludeList)
            for i in range(NumExclude):
                ExcludeDateList = ast.literal_eval(cf['Variables'][ThisOne]['ExcludeDates'][str(i)])
                try:
                    si = ldt.index(datetime.datetime.strptime(ExcludeDateList[0],'%Y-%m-%d %H:%M'))
                except ValueError:
                    si = 0
                try:
                    ei = ldt.index(datetime.datetime.strptime(ExcludeDateList[1],'%Y-%m-%d %H:%M')) + 1
                except ValueError:
                    ei = -1
                ds.series[ThisOne]['Data'][si:ei] = float(-9999)
                ds.series[ThisOne]['Flag'][si:ei] = 6
                ds.series[ThisOne]['Attr']['ExcludeDates_'+str(i)] = cf['Variables'][ThisOne]['ExcludeDates'][str(i)]

def do_excludehours(cf,ds,ThisOne):
    if ThisOne in cf['Variables'].keys():
        if 'ExcludeHours' in cf['Variables'][ThisOne].keys():
            ldt = ds.series['DateTime']['Data']
            ExcludeList = cf['Variables'][ThisOne]['ExcludeHours'].keys()
            NumExclude = len(ExcludeList)
            for i in range(NumExclude):
                ExcludeHourList = ast.literal_eval(cf['Variables'][ThisOne]['ExcludeHours'][str(i)])
                try:
                    si = ldt.index(datetime.datetime.strptime(ExcludeHourList[0],'%Y-%m-%d %H:%M'))
                except ValueError:
                    si = 0
                try:
                    ei = ldt.index(datetime.datetime.strptime(ExcludeHourList[1],'%Y-%m-%d %H:%M')) + 1
                except ValueError:
                    ei = -1
                for j in range(len(ExcludeHourList[2])):
                    ExHr = datetime.datetime.strptime(ExcludeHourList[2][j],'%H:%M').hour
                    ExMn = datetime.datetime.strptime(ExcludeHourList[2][j],'%H:%M').minute
                    index = numpy.where((ds.series['Hour']['Data'][si:ei]==ExHr)&
                                        (ds.series['Minute']['Data'][si:ei]==ExMn))[0] + si
                    ds.series[ThisOne]['Data'][index] = float(-9999)
                    ds.series[ThisOne]['Flag'][index] = 7
                    ds.series[ThisOne]['Attr']['ExcludeHours_'+str(i)] = cf['Variables'][ThisOne]['ExcludeHours'][str(i)]

def do_linear(cf,ds):
    for ThisOne in cf['Variables'].keys():
        if qcutils.haskey(cf,ThisOne,'Linear'):
            qcts.ApplyLinear(cf,ds,ThisOne)
        if qcutils.haskey(cf,ThisOne,'Drift'):
            qcts.ApplyLinearDrift(cf,ds,ThisOne)
        if qcutils.haskey(cf,ThisOne,'LocalDrift'):
            qcts.ApplyLinearDriftLocal(cf,ds,ThisOne)

def do_rangecheck(cf,ds,ThisOne,code=2):
    '''Applies a range check to data series listed in the control file.  Data values that
       are less than the lower limit or greater than the upper limit are replaced with
       -9999 and the corresponding QC flag element is set to 2.'''
    # loop over the series in the data structure
    if ThisOne in cf['Variables'].keys():
        if 'RangeCheck' in cf['Variables'][ThisOne].keys():
            if 'Lower' in cf['Variables'][ThisOne]['RangeCheck'].keys():
                lwr = numpy.array(eval(cf['Variables'][ThisOne]['RangeCheck']['Lower']))
                lwr = lwr[ds.series['Month']['Data']-1]
                index = numpy.where((abs(ds.series[ThisOne]['Data']-numpy.float64(-9999))>c.eps)&
                                        (ds.series[ThisOne]['Data']<lwr))
                ds.series[ThisOne]['Data'][index] = numpy.float64(-9999)
                ds.series[ThisOne]['Flag'][index] = code
                ds.series[ThisOne]['Attr']['RangeCheck_Lower'] = cf['Variables'][ThisOne]['RangeCheck']['Lower']
            if 'Upper' in cf['Variables'][ThisOne]['RangeCheck'].keys():
                upr = numpy.array(eval(cf['Variables'][ThisOne]['RangeCheck']['Upper']))
                upr = upr[ds.series['Month']['Data']-1]
                index = numpy.where((abs(ds.series[ThisOne]['Data']-numpy.float64(-9999))>c.eps)&
                                        (ds.series[ThisOne]['Data']>upr))
                ds.series[ThisOne]['Data'][index] = numpy.float64(-9999)
                ds.series[ThisOne]['Flag'][index] = code
                ds.series[ThisOne]['Attr']['RangeCheck_Upper'] = cf['Variables'][ThisOne]['RangeCheck']['Upper']

def do_qcchecks(cf,ds,series=''):
    level = ds.globalattributes['Level']
    if level == 'L3':
        range_code = 16
        diurnal_code = 17
    if level == 'L4':
        range_code = 82
        diurnal_code = 83
    if len(series)==0:
        series = cf['Variables'].keys()
    # do the range check
    for ThisOne in series:
        do_rangecheck(cf,ds,ThisOne,range_code)
    log.info(' Finished the range check at level '+level)
    # do the diurnal check
    for ThisOne in series:
        do_diurnalcheck(cf,ds,ThisOne,diurnal_code)
    log.info(' Finished the diurnal average check at level '+level)

def gaps(cf,ds,Fc_in='Fc',Fe_in='Fe',Fh_in='Fh'):
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='gapsvars'):
        vars = ast.literal_eval(cf['FunctionArgs']['gapsvars'])
        Fc_in = vars[0]
        Fe_in = vars[1]
        Fh_in = vars[2]
    Fc,flagC = qcutils.GetSeriesasMA(ds,Fc_in)
    Fe,flagE = qcutils.GetSeriesasMA(ds,Fe_in)
    Fh,flagH = qcutils.GetSeriesasMA(ds,Fh_in)
    index = numpy.ma.where((numpy.mod(flagC,10)!=0) | (numpy.mod(flagE,10)!=0) | (numpy.mod(flagH,10)!=0))[0]
    rC_i = numpy.ma.where((numpy.mod(flagC,10)==0) & ((numpy.mod(flagE,10)!=0) | (numpy.mod(flagH,10)!=0)))[0]
    rE_i = numpy.ma.where((numpy.mod(flagE,10)==0) & ((numpy.mod(flagC,10)!=0) | (numpy.mod(flagH,10)!=0)))[0]
    rH_i = numpy.ma.where((numpy.mod(flagH,10)==0) & ((numpy.mod(flagC,10)!=0) | (numpy.mod(flagE,10)!=0)))[0]
    ds.series[Fc_in]['Flag'][rC_i] = 19
    ds.series[Fe_in]['Flag'][rE_i] = 19
    ds.series[Fh_in]['Flag'][rH_i] = 19
    flux_series = [Fc_in,Fe_in,Fh_in]
    for ThisOne in flux_series:
        index = numpy.where(ds.series[ThisOne]['Flag'] == 19)[0]
        ds.series[ThisOne]['Data'][index] = float(-9999)
    log.info(' Finished gap co-ordination')

