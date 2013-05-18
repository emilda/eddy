"""
    QC Data Function Module
    Used to perform the tasks queued by qcls.py
    """

import sys
import ast
from calendar import isleap
import constants as c
import datetime
from matplotlib.dates import date2num
import meteorologicalfunctions as mf
import numpy
import qcck
import qcio
import qcts
import qcutils
from scipy import interpolate
import time
import xlrd
from matplotlib.mlab import griddata
import xlwt
import logging
import math
import csv


log = logging.getLogger('qc.ts')

def albedo(cf,ds):
    """
        Filter albedo measurements to:
            high solar angle specified by periods between 10.00 and 14.00, inclusive
            and
            full sunlight in which Fsd > 290 W/m2
        
        Usage qcts.albedo(ds)
        ds: data structure
        """
    log.info(' Applying albedo constraints')
    if 'Fsd' in ds.series.keys() and 'Fsu' in ds.series.keys() and 'albedo' in ds.series.keys():
        nightindex = numpy.ma.where((ds.series['Fsd']['Data'] < 5) | (ds.series['Fsu']['Data'] < 2))[0]
        ds.series['Fsd']['Data'][nightindex] = 0.
        ds.series['Fsu']['Data'][nightindex] = 0.
        ds.series['albedo']['Data'][nightindex] = 0.
    
    if 'albedo' not in ds.series.keys():
        if 'Fsd' in ds.series.keys() and 'Fsu' in ds.series.keys():
            Fsd,f = qcutils.GetSeriesasMA(ds,'Fsd')
            Fsu,f = qcutils.GetSeriesasMA(ds,'Fsu')
            albedo = Fsu / Fsd
            qcutils.CreateSeries(ds,'albedo',albedo,FList=['Fsd','Fsu'],Descr='solar albedo',Units='unitless',Standard='solar_albedo')
        else:
            log.warning('  Fsd or Fsu not in ds, albedo not calculated')
            return
    else:
        albedo,f = qcutils.GetSeriesasMA(ds,'albedo')
        if 'Fsd' in ds.series.keys():
            Fsd,f = qcutils.GetSeriesasMA(ds,'Fsd')
        else:
            Fsd,f = qcutils.GetSeriesasMA(ds,'Fn')
    
    if qcutils.cfkeycheck(cf,ThisOne='albedo',key='Threshold'):
        Fsdbase = float(cf['Variables']['albedo']['Threshold']['Fsd'])
        ds.series['albedo']['Attr']['FsdCutoff'] = Fsdbase
    else:
        Fsdbase = 290.
    index = numpy.ma.where((Fsd < Fsdbase) | (ds.series['Hdh']['Data'] < 10) | (ds.series['Hdh']['Data'] > 14))[0]
    index1 = numpy.ma.where(Fsd < Fsdbase)[0]
    index2 = numpy.ma.where((ds.series['Hdh']['Data'] < 10) | (ds.series['Hdh']['Data'] > 14))[0]
    albedo[index] = numpy.float64(-9999)
    ds.series['albedo']['Flag'][index1] = 8     # bad Fsd flag only if bad time flag not set
    ds.series['albedo']['Flag'][index2] = 9     # bad time flag
    ds.series['albedo']['Data']=numpy.ma.filled(albedo,float(-9999))

def ApplyLinear(cf,ds,ThisOne):
    """
        Applies a linear correction to variable passed from qcls. Time period
        to apply the correction, slope and offset are specified in the control
        file.
        
        Usage qcts.ApplyLinear(cf,ds,x)
        cf: control file
        ds: data structure
        x: input/output variable in ds.  Example: 'Cc_7500_Av'
        """
    log.info('  Applying linear correction to '+ThisOne)
    if qcutils.incf(cf,ThisOne) and qcutils.haskey(cf,ThisOne,'Linear'):
        data = numpy.ma.masked_where(ds.series[ThisOne]['Data']==float(-9999),ds.series[ThisOne]['Data'])
        flag = ds.series[ThisOne]['Flag'].copy()
        ldt = ds.series['DateTime']['Data']
        LinearList = cf['Variables'][ThisOne]['Linear'].keys()
        for i in range(len(LinearList)):
            LinearItemList = ast.literal_eval(cf['Variables'][ThisOne]['Linear'][str(i)])
            try:
                si = ldt.index(datetime.datetime.strptime(LinearItemList[0],'%Y-%m-%d %H:%M'))
            except ValueError:
                si = 0
            try:
                ei = ldt.index(datetime.datetime.strptime(LinearItemList[1],'%Y-%m-%d %H:%M')) + 1
            except ValueError:
                ei = -1
            Slope = float(LinearItemList[2])
            Offset = float(LinearItemList[3])
            data[si:ei] = Slope * data[si:ei] + Offset
            index = numpy.where(flag[si:ei]==0)[0]
            flag[si:ei][index] = 10
            ds.series[ThisOne]['Data'] = numpy.ma.filled(data,float(-9999))
            ds.series[ThisOne]['Flag'] = flag

def ApplyLinearDrift(cf,ds,ThisOne):
    """
        Applies a linear correction to variable passed from qcls. The slope is
        interpolated for each 30-min period between the starting value at time 0
        and the ending value at time 1.  Slope0, Slope1 and Offset are defined
        in the control file.  This function applies to a dataset in which the
        start and end times in the control file are matched by the time period
        in the dataset.
        
        Usage qcts.ApplyLinearDrift(cf,ds,x)
        cf: control file
        ds: data structure
        x: input/output variable in ds.  Example: 'Cc_7500_Av'
        """
    log.info('  Applying linear drift correction to '+ThisOne)
    if qcutils.incf(cf,ThisOne) and qcutils.haskey(cf,ThisOne,'Drift'):
        data = numpy.ma.masked_where(ds.series[ThisOne]['Data']==float(-9999),ds.series[ThisOne]['Data'])
        flag = ds.series[ThisOne]['Flag']
        ldt = ds.series['DateTime']['Data']
        DriftList = cf['Variables'][ThisOne]['Drift'].keys()
        for i in range(len(DriftList)):
            DriftItemList = ast.literal_eval(cf['Variables'][ThisOne]['Drift'][str(i)])
            try:
                si = ldt.index(datetime.datetime.strptime(DriftItemList[0],'%Y-%m-%d %H:%M'))
            except ValueError:
                si = 0
            try:
                ei = ldt.index(datetime.datetime.strptime(DriftItemList[1],'%Y-%m-%d %H:%M')) + 1
            except ValueError:
                ei = -1
            Slope = numpy.zeros(len(data))
            Slope0 = float(DriftItemList[2])
            Slope1 = float(DriftItemList[3])
            Offset = float(DriftItemList[4])
            nRecs = len(Slope[si:ei])
            for i in range(nRecs):
                ssi = si + i
                Slope[ssi] = ((((Slope1 - Slope0) / nRecs) * i) + Slope0)
            data[si:ei] = Slope[si:ei] * data[si:ei] + Offset
            flag[si:ei] = 10
            ds.series[ThisOne]['Data'] = numpy.ma.filled(data,float(-9999))
            ds.series[ThisOne]['Flag'] = flag

def ApplyLinearDriftLocal(cf,ds,ThisOne):
    """
        Applies a linear correction to variable passed from qcls. The slope is
        interpolated since the starting value at time 0 using a known 30-min
        increment.  Slope0, SlopeIncrement and Offset are defined in the control
        file.  This function applies to a dataset in which the start time in the
        control file is matched by dataset start time, but in which the end time
        in the control file extends beyond the dataset end.
        
        Usage qcts.ApplyLinearDriftLocal(cf,ds,x)
        cf: control file
        ds: data structure
        x: input/output variable in ds.  Example: 'Cc_7500_Av'
        """
    log.info('  Applying linear drift correction to '+ThisOne)
    if qcutils.incf(cf,ThisOne) and qcutils.haskey(cf,ThisOne,'LocalDrift'):
        data = numpy.ma.masked_where(ds.series[ThisOne]['Data']==float(-9999),ds.series[ThisOne]['Data'])
        flag = ds.series[ThisOne]['Flag']
        ldt = ds.series['DateTime']['Data']
        DriftList = cf['Variables'][ThisOne]['LocalDrift'].keys()
        for i in range(len(DriftList)):
            DriftItemList = ast.literal_eval(cf['Variables'][ThisOne]['LocalDrift'][str(i)])
            try:
                si = ldt.index(datetime.datetime.strptime(DriftItemList[0],'%Y-%m-%d %H:%M'))
            except ValueError:
                si = 0
            try:
                ei = ldt.index(datetime.datetime.strptime(DriftItemList[1],'%Y-%m-%d %H:%M')) + 1
            except ValueError:
                ei = -1
            Slope = numpy.zeros(len(data))
            Slope0 = float(DriftItemList[2])
            SlopeIncrement = float(DriftItemList[3])
            Offset = float(DriftItemList[4])
            nRecs = len(Slope[si:ei])
            for i in range(nRecs):
                ssi = si + i
                Slope[ssi] = (SlopeIncrement * i) + Slope0
            data[si:ei] = Slope[si:ei] * data[si:ei] + Offset
            flag[si:ei] = 10
            ds.series[ThisOne]['Data'] = numpy.ma.filled(data,float(-9999))
            ds.series[ThisOne]['Flag'] = flag

def AverageSeriesByElements(ds,Av_out,Series_in):
    """
        Calculates the average of multiple time series.  Multiple time series
        are entered and a single time series representing the average at each
        observational period is returned.
        
        Usage qcts.AverageSeriesByElements(ds,Av_out,Series_in)
        ds: data structure
        Av_out: output variable to ds.  Example: 'Fg_Av'
        Series_in: input variable series in ds.  Example: ['Fg_1','Fg_2']
        """
    log.info(' Averaging series in '+str(Series_in)+' into '+str(Av_out))
    nSeries = len(Series_in)
    if nSeries==0:
        log.error('  AverageSeriesByElements: no input series specified')
        return
    if nSeries==1:
        TmpArr_data = ds.series[Series_in[0]]['Data'].copy()
        TmpArr_flag = ds.series[Series_in[0]]['Flag'].copy()
        Av_data = numpy.ma.masked_where(TmpArr_data==float(-9999),TmpArr_data)
        Mx_flag = TmpArr_flag
        SeriesNameString = Series_in[0]
        SeriesUnitString = ds.series[Series_in[0]]['Attr']['units']
    else:
        TmpArr_data = ds.series[Series_in[0]]['Data'].copy()
        TmpArr_flag = ds.series[Series_in[0]]['Flag'].copy()
        SeriesNameString = Series_in[0]
        Series_in.remove(Series_in[0])
        for ThisOne in Series_in:
            SeriesNameString = SeriesNameString+', '+ThisOne
            TmpArr_data = numpy.vstack((TmpArr_data,ds.series[ThisOne]['Data'].copy()))
            TmpArr_flag = numpy.vstack((TmpArr_flag,ds.series[ThisOne]['Flag'].copy()))
        TmpArr_data = numpy.ma.masked_where(TmpArr_data==float(-9999),TmpArr_data)
        Av_data = numpy.ma.average(TmpArr_data,axis=0)
        Mx_flag = numpy.min(TmpArr_flag,axis=0)
    DStr = 'Element-wise average of series '+SeriesNameString
    UStr = ds.series[Series_in[0]]['Attr']['units']
    SStr = ds.series[Series_in[0]]['Attr']['standard_name']
    qcutils.CreateSeries(ds,Av_out,Av_data,FList=Series_in,Descr=DStr,Units=UStr,Standard=SStr)

def BypassTcorr(cf,ds):
    if qcutils.cfkeycheck(cf,Base='Soil',ThisOne='BypassTcorrList'):
        subkeys = ast.literal_eval(cf['Soil']['BypassTcorrList'])
        for i in range(len(subkeys)):
            if subkeys[i] in ds.series.keys():
                Sws,f = qcutils.GetSeriesasMA(ds,subkeys[i])
                Sws_bypass = -0.0663 + -0.0063 * Sws + 0.0007 * Sws ** 2
                qcutils.CreateSeries(ds,subkeys[i],Sws_bypass,FList=[subkeys[i]],Descr=ds.series[subkeys[i]]['Attr']['long_name'],Units='frac',Standard='soil_moisture_content')
    else:
        for ThisOne in ds.series.keys():
            if 'Sws' in ThisOne:
                Sws,f = qcutils.GetSeriesasMA(ds,ThisOne)
                Sws_bypass = -0.0663 + -0.0063 * Sws + 0.0007 * Sws ** 2
                qcutils.CreateSeries(ds,ThisOne,Sws_bypass,FList=[ThisOne],Descr=ds.series[ThisOne]['Attr']['long_name'],Units='frac',Standard='soil_moisture_content')

def CalculateAhHMP(cf,ds,e_name='e',Ta_name='Ta_HMP',Ah_name='Ah_HMP'):
    """
        Calculate the absolute humidity from vapour pressure and temperature.
        
        """
    log.info(' Calculating Ah from vapour pressure and air temperature')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='AhVars'):
        vars = ast.literal_eval(cf['FunctionArgs']['AhVars'])
        e_name = vars[0]
        Ta_name = vars[1]
        Ah_name = vars[2]
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_name)
    e,f = qcutils.GetSeriesasMA(ds,e_name)
    Ah = mf.absolutehumidity(Ta,e)
    qcutils.CreateSeries(ds,Ah_name,Ah,FList=[Ta_name,e_name],Descr='Absolute humidity (HMP)',Units='g/m3')

def CalculateAvailableEnergy(cf,ds,Fa_out='Fa',Fn_in='Fn',Fg_in='Fg'):
    """
        Calculate the average energy as Fn - G.
        
        Usage qcts.CalculateAvailableEnergy(ds,Fa_out,Fn_in,Fg_in)
        ds: data structure
        Fa_out: output available energy variable to ds.  Example: 'Fa'
        Fn_in: input net radiation in ds.  Example: 'Fn'
        Fg_in: input ground heat flux in ds.  Example: 'Fg'
        """
    log.info(' Calculating available energy from Fn and Fg')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='Avail'):
        arg = ast.literal_eval(cf['FunctionArgs']['Avail'])
        Fa_out = arg[0]
        Fn_in = arg[1]
        Fg_in = arg[2]
    Fn,f = qcutils.GetSeriesasMA(ds,Fn_in)
    Fg,f = qcutils.GetSeriesasMA(ds,Fg_in)
    Fa = Fn - Fg
    qcutils.CreateSeries(ds,Fa_out,Fa,FList=[Fn_in,Fg_in],
                         Descr='Available energy using '+Fn_in+','+Fg_in,
                         Units='W/m2')

def CalculateET(cf,ds,level,Fe_in='Fe'):
    if qcutils.cfkeycheck(cf,Base='CalculateET',ThisOne='Fe_in'):
        Fe_in = cf['Sums']['Fe_in']
    Fe,f = qcutils.GetSeriesasMA(ds,Fe_in)
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    ET = Fe * 60 * 30 * 1000 / (Lv * c.rho_water)  # mm/30min for summing
    if 'ET' not in ds.series.keys():
        qcutils.CreateSeries(ds,'ET',ET,FList=[Fe_in],Descr='Evapotranspiration Flux',Units='mm/30min')
        ds.series['ET']['Attr']['Level'] = level
    elif ds.series['ET']['Attr']['Level'] == level:
        log.warn('   ET already in dataset at level '+level+': ET not re-computed')
    else:
        qcutils.CreateSeries(ds,'ET',ET,FList=[Fe_in],Descr='Evapotranspiration Flux',Units='mm/30min')
        ds.series['ET']['Attr']['Level'] = level
    
def CalculateFluxes(cf,ds,massman='False',Ta_name='Ta',ps_name='ps',Ah_name='Ah',wT_in='wT',wA_in='wA',wC_in='wC',uw_in='uw',vw_in='vw',Fh_out='Fh',Fe_out='Fe',Fc_out='Fc',Fm_out='Fm',ustar_out='ustar'):
    """
        Calculate the fluxes from the rotated covariances.
        
        Usage qcts.CalculateFluxes(ds)
        ds: data structure
        
        Pre-requisite: CoordRotation2D
        
        Accepts meteorological constants or variables
        """
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='CF'):
        args = ast.literal_eval(cf['FunctionArgs']['CF'])
        Ta_name = args[0]
        Ah_name = args[1]
        ps_name = args[2]
        wT_in = args[3]
        wA_in = args[4]
        wC_in = args[5]
        uw_in = args[6]
        vw_in = args[7]
        Fh_out = args[8]
        Fe_out = args[9]
        Fc_out = args[10]
        Fm_out = args[11]
        ustar_out = args[12]
    long_name = ''
    if massman == 'True':
        long_name = ' and frequency response corrected'
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_name)
    ps,f = qcutils.GetSeriesasMA(ds,ps_name)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_name)
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
        
    log.info(' Calculating fluxes from covariances')
    if wT_in in ds.series.keys():
        wT,f = qcutils.GetSeriesasMA(ds,wT_in)
        Fh = rhom * c.Cpd * wT
        qcutils.CreateSeries(ds,Fh_out,Fh,FList=[wT_in],Descr='Sensible heat flux, rotated to natural wind coordinates'+long_name,Units='W/m2',Standard='surface_upward_sensible_heat_flux')
        flagindex = numpy.where(numpy.mod(ds.series[Fh_out]['Flag'],10)!=0)[0]
        ds.series[Fh_out]['Data'][flagindex] = numpy.float(-9999)
    else:
        log.error('  CalculateFluxes: '+wT_in+' not found in ds.series, Fh not calculated')
    if wA_in in ds.series.keys():
        wA,f = qcutils.GetSeriesasMA(ds,wA_in)
        if 'Lv' in ds.series.keys():
            Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
            Fe = Lv * wA / float(1000)
        else:
            Fe = c.Lv * wA / float(1000)
        qcutils.CreateSeries(ds,Fe_out,Fe,FList=[wA_in],Descr='Latent heat flux, rotated to natural wind coordinates'+long_name,Units='W/m2',Standard='surface_upward_latent_heat_flux')
        flagindex = numpy.where(numpy.mod(ds.series[Fe_out]['Flag'],10)!=0)[0]
        ds.series[Fe_out]['Data'][flagindex] = numpy.float(-9999)
    else:
        log.error('  CalculateFluxes: '+wA_in+' not found in ds.series, Fe not calculated')
    if wC_in in ds.series.keys():
        wC,f = qcutils.GetSeriesasMA(ds,wC_in)
        Fc = wC
        qcutils.CreateSeries(ds,Fc_out,Fc,FList=[wC_in],Descr='CO2 flux, rotated to natural wind coordinates'+long_name,Units='mg/m2/s')
        flagindex = numpy.where(numpy.mod(ds.series[Fc_out]['Flag'],10)!=0)[0]
        ds.series[Fc_out]['Data'][flagindex] = numpy.float(-9999)
    else:
        log.error('  CalculateFluxes: '+wC_in+' not found in ds.series, Fc_raw not calculated')
    if uw_in in ds.series.keys():
        if vw_in in ds.series.keys():
            uw,f = qcutils.GetSeriesasMA(ds,uw_in)
            vw,f = qcutils.GetSeriesasMA(ds,vw_in)
            vs = uw*uw + vw*vw
            Fm = rhom * numpy.ma.sqrt(vs)
            us = numpy.ma.sqrt(numpy.ma.sqrt(vs))
            qcutils.CreateSeries(ds,Fm_out,Fm,FList=[uw_in,vw_in],Descr='Momentum flux, rotated to natural wind coordinates'+long_name,Units='kg/m/s2')
            qcutils.CreateSeries(ds,ustar_out,us,FList=[uw_in,vw_in],Descr='Friction velocity, rotated to natural wind coordinates'+long_name,Units='m/s')
            for ThisOne in [Fm_out,ustar_out]:
                flagindex = numpy.where(numpy.mod(ds.series[ThisOne]['Flag'],10)!=0)[0]
                ds.series[ThisOne]['Data'][flagindex] = numpy.float(-9999)
        else:
            log.error('  CalculateFluxes: wy not found in ds.series, Fm and ustar not calculated')
    else:
        log.error('  CalculateFluxes: wx not found in ds.series, Fm and ustar not calculated')

def CalculateLongwave(ds,Fl_out,Fl_in,Tbody_in):
    """
        Calculate the longwave radiation given the raw thermopile output and the
        sensor body temperature.
        
        Usage qcts.CalculateLongwave(ds,Fl_out,Fl_in,Tbody_in)
        ds: data structure
        Fl_out: output longwave variable to ds.  Example: 'Flu'
        Fl_in: input longwave in ds.  Example: 'Flu_raw'
        Tbody_in: input sensor body temperature in ds.  Example: 'Tbody'
        """
    log.info(' Calculating longwave radiation')
    Fl_raw,f = qcutils.GetSeriesasMA(ds,Fl_in)
    Tbody,f = qcutils.GetSeriesasMA(ds,Tbody_in)
    Fl = Fl_raw + c.sb*(Tbody + 273.15)**4
    qcutils.CreateSeries(ds,Fl_out,Fl,FList=[Fl_in,Tbody_in],
                         Descr='Calculated longwave radiation using '+Fl_in+','+Tbody_in,
                         Units='W/m2')

def CalculateMeteorologicalVariables(cf,ds,Ta_name='Ta',ps_name='ps',Ah_name='Ah'):
    """
        Add time series of meteorological variables based on fundamental
        relationships (Stull 1988)

        Usage qcts.CalculateMeteorologicalVariables(ds,Ta_name,ps_name,Ah_name)
        ds: data structure
        Ta_name: data series name for air temperature
        ps_name: data series name for pressure
        Ah_name: data series name for absolute humidity

        Variables added:
            rhom: density of moist air, mf.densitymoistair(Ta,ps,Ah)
            Lv: latent heat of vapourisation, mf.Lv(Ta)
            q: specific humidity, mf.specifichumidity(mr)
                where mr (mixing ratio) = mf.mixingratio(ps,vp)
            Cpm: specific heat of moist air, mf.specificheatmoistair(q)
            VPD: vapour pressure deficit, VPD = esat - e
        """
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='MetVars'):
        vars = ast.literal_eval(cf['FunctionArgs']['MetVars'])
        Ta_name = vars[0]
        ps_name = vars[1]
        Ah_name = vars[2]
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_name)
    ps,f = qcutils.GetSeriesasMA(ds,ps_name)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_name)
    
    if 'e' in ds.series.keys():
        e,f = qcutils.GetSeriesasMA(ds,'e')
    else:
        e = mf.vapourpressure(Ah,Ta)
        qcutils.CreateSeries(ds,'e',e,FList=[Ta_name,Ah_name],Descr='Vapour pressure',Units='kPa',Standard='water_vapor_partial_pressure_in_air')
    if 'esat' in ds.series.keys():
        esat,f = qcutils.GetSeriesasMA(ds,'esat')
    else:
        esat = mf.es(Ta)
        qcutils.CreateSeries(ds,'esat',esat,FList=[Ta_name],Descr='saturation vapour pressure (HMP)',Units='kPa')
    if 'rhod' not in ds.series.keys():
        rhod = mf.densitydryair(Ta,ps)
        qcutils.CreateSeries(ds,'rhod',rhod,FList=[Ta_name,ps_name],Descr='Density of dry air',Units='kg/m3')
    if 'rhom' not in ds.series.keys():
        rhom = mf.densitymoistair(Ta,ps,Ah)
        qcutils.CreateSeries(ds,'rhom',rhom,FList=[Ta_name,ps_name,Ah_name],Descr='Density of moist air',Units='kg/m3',Standard='air_density')
    Lv = mf.Lv(Ta)
    mr = mf.mixingratio(ps,e)
    mrsat = mf.mixingratio(ps,esat)
    q = mf.specifichumidity(mr)
    qsat = mf.specifichumidity(mrsat)
    Cpm = mf.specificheatmoistair(q)
    VPD = esat - e
    SHD = qsat - q
    qcutils.CreateSeries(ds,'Lv',Lv,FList=[Ta_name],Descr='Latent heat of vapourisation',Units='J/kg')
    qcutils.CreateSeries(ds,'Cpm',Cpm,FList=[Ta_name,ps_name,Ah_name],Descr='Specific heat of moist air',Units='J/kg-K')
    qcutils.CreateSeries(ds,'q',q,FList=[Ta_name,ps_name,Ah_name],Descr='Specific humidity',Units='kg/kg',Standard='specific_humidity')
    qcutils.CreateSeries(ds,'VPD',VPD,FList=[Ta_name,Ah_name],Descr='Vapour pressure deficit',Units='kPa',Standard='water_vapor_saturation_deficit_in_air')
    qcutils.CreateSeries(ds,'SHD',SHD,FList=[Ta_name,Ah_name],Descr='Specific humidity deficit',Units='kg/kg')
    qcutils.CreateSeries(ds,'mr',mr,FList=[Ta_name,ps_name,Ah_name],Descr='Mixing ratio',Units='kg/kg',Standard='humidity_mixing_ratio')

def CalculateNetRadiation(ds,Fn_out,Fsd_in,Fsu_in,Fld_in,Flu_in):
    """
        Calculate the net radiation from the 4 components of the surface
        radiation budget.
        
        Usage qcts.CalculateNetRadiation(ds,Fn_out,Fsd_in,Fsu_in,Fld_in,Flu_in)
        ds: data structure
        Fn_out: output net radiation variable to ds.  Example: 'Fn_KZ'
        Fsd_in: input downwelling solar radiation in ds.  Example: 'Fsd'
        Fsu_in: input upwelling solar radiation in ds.  Example: 'Fsu'
        Fld_in: input downwelling longwave radiation in ds.  Example: 'Fld'
        Flu_in: input upwelling longwave radiation in ds.  Example: 'Flu'
        """
    log.info(' Calculating net radiation from 4 components')
    if Fsd_in in ds.series.keys() and Fsu_in in ds.series.keys() and Fld_in in ds.series.keys() and Flu_in in ds.series.keys():
        Fsd,f = qcutils.GetSeriesasMA(ds,Fsd_in)
        Fsu,f = qcutils.GetSeriesasMA(ds,Fsu_in)
        Fld,f = qcutils.GetSeriesasMA(ds,Fld_in)
        Flu,f = qcutils.GetSeriesasMA(ds,Flu_in)
        Fn = (Fsd - Fsu) + (Fld - Flu)
        qcutils.CreateSeries(ds,Fn_out,Fn,FList=[Fsd_in,Fsu_in,Fld_in,Flu_in],
                             Descr='Calculated net radiation using '+Fsd_in+','+Fsu_in+','+Fld_in+','+Flu_in,
                             Units='W/m2')
    else:
        nRecs = len(ds.series['xlDateTime']['Data'])
        ds.series[Fn_out] = {}
        ds.series[Fn_out]['Data'] = numpy.zeros(nRecs) + float(-9999)
        ds.series[Fn_out]['Flag'] = numpy.zeros(nRecs) + float(1)
        ds.series[Fn_out]['Attr'] = {}
        ds.series[Fn_out]['Attr']['long_name'] = 'Calculated net radiation (one or more components missing)'
        ds.series[Fn_out]['Attr']['units'] = 'W/m2'

def CalculateSpecificHumidityProfile(cf,ds):
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='ps_in'):
        ps_in = cf['qTprofile']['p_in']
    else:
        ps_in = 'ps'
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='Ta_in'):
        Ta_in = ast.literal_eval(cf['qTprofile']['Ta_in'])
    else:
        log.error('  No input air temperature variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='e_in'):
        e_vars = ast.literal_eval(cf['qTprofile']['e_in'])
    else:
        log.error('  No input vapour pressure variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='esat_in'):
        esat_vars = ast.literal_eval(cf['qTprofile']['esat_in'])
    else:
        log.error('  No input saturation vapour pressure variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='q_out'):
        q_vars = ast.literal_eval(cf['qTprofile']['q_out'])
    else:
        log.error('  No output specific humidity variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='qsat_out'):
        qsat_vars = ast.literal_eval(cf['qTprofile']['qsat_out'])
    else:
        log.error('  No output saturation specific humidity variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='VPD_out'):
        VPD_vars = ast.literal_eval(cf['qTprofile']['VPD_out'])
    else:
        log.error('  No output vapour pressure deficit variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='mr_out'):
        mr_vars = ast.literal_eval(cf['qTprofile']['mr_out'])
    else:
        log.error('  No output mixing ratio variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='Tv_out'):
        Tv_vars = ast.literal_eval(cf['qTprofile']['Tv_out'])
    else:
        log.error('  No output virtual temperature variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='Tvp_out'):
        Tvp_vars = ast.literal_eval(cf['qTprofile']['Tvp_out'])
    else:
        log.error('  No output virtual potential temperature variables identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='q_attr'):
        q_attrs = ast.literal_eval(cf['qTprofile']['q_attr'])
    else:
        log.error('  Specific humidity attributes not identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='qsat_attr'):
        qsat_attrs = ast.literal_eval(cf['qTprofile']['qsat_attr'])
    else:
        log.error('  Saturated specific humidity attributes not identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='VPD_attr'):
        VPD_attrs = ast.literal_eval(cf['qTprofile']['VPD_attr'])
    else:
        log.error('  Vapour pressure deficit attributes not identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='mr_attr'):
        mr_attrs = ast.literal_eval(cf['qTprofile']['mr_attr'])
    else:
        log.error('  Mixing ratio attributes not identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='Tv_attr'):
        Tv_attrs = ast.literal_eval(cf['qTprofile']['Tv_attr'])
    else:
        log.error('  Virtual temperature attributes not identified')
        return
    
    if qcutils.cfkeycheck(cf,Base='qTprofile',ThisOne='Tvp_attr'):
        Tvp_attrs = ast.literal_eval(cf['qTprofile']['Tvp_attr'])
    else:
        log.error('  Virtual potential temperature attributes not identified')
        return
    
    if (len(e_vars) != len(q_vars) != len(q_attrs) != len(VPD_vars) != len(mr_vars) != len(Tv_vars) != len(Tvp_vars) != len(esat_vars) != len(qsat_vars) != len(qsat_attrs) != len(VPD_attrs) != len(mr_attrs) != len(Tv_attrs) != len(Tvp_attrs)):
        log.error('  Input and output vectors not of equal length')
        return
    
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    for i in range(len(e_vars)):
        Ta,f = qcutils.GetSeriesasMA(ds,Ta_in[i])
        e,f = qcutils.GetSeriesasMA(ds,e_vars[i])
        esat,f = qcutils.GetSeriesasMA(ds,esat_vars[i])
        mr = mf.mixingratio(ps,e)
        q = mf.specifichumidity(mr)
        mrsat = mf.mixingratio(ps,esat)
        qsat = mf.specifichumidity(mrsat)
        VPD = esat - e
        Tv = mf.theta(Ta,ps)
        Tvp = mf.virtualtheta(Tv,mr)
        qcutils.CreateSeries(ds,q_vars[i],q,FList=[ps_in,e_vars[i]],Descr=q_attrs[i],Units='kg/kg',Standard='specific_humidity')
        qcutils.CreateSeries(ds,qsat_vars[i],qsat,FList=[ps_in,esat_vars[i]],Descr=qsat_attrs[i],Units='kg/kg',Standard='not_defined')
        qcutils.CreateSeries(ds,VPD_vars[i],VPD,FList=[ps_in,e_vars[i],esat_vars[i]],Descr=VPD_attrs[i],Units='kPa',Standard='water_vapor_saturation_deficit_in_air')
        qcutils.CreateSeries(ds,mr_vars[i],mr,FList=[ps_in,e_vars[i]],Descr=mr_attrs[i],Units='kg/kg',Standard='humidity_mixing_ratio')
        qcutils.CreateSeries(ds,Tv_vars[i],Tv,FList=[ps_in,Ta_in[i]],Descr=Tv_attrs[i],Units='C',Standard='virtual_temperature')
        qcutils.CreateSeries(ds,Tvp_vars[i],Tvp,FList=[ps_in,e_vars[i],Ta_in[i]],Descr=Tvp_attrs[i],Units='C')
    
    log.info(' q and T profile computed')
    return

def ComputeClimatology(cf,ds,OList):
    if qcutils.cfkeycheck(cf,Base='Climatology',ThisOne='EF'):
        efflag = cf['Climatology']['EF']
    else:
        efflag = 'True'
    
    if qcutils.cfkeycheck(cf,Base='Climatology',ThisOne='BR'):
        brflag = cf['Climatology']['BR']
    else:
        brflag = 'True'
    
    if qcutils.cfkeycheck(cf,Base='Climatology',ThisOne='WUE'):
        wueflag = cf['Climatology']['WUE']
    else:
        wueflag = 'True'
    
    if ((efflag != 'True') & (brflag != 'True') & (wueflag != 'True') & (len(OList) == 0)):
        log.warn('  Climatology:  no dataset to generate')
        return
    
    log.info(' Computing climatology...')
    if qcutils.cfkeycheck(cf,Base='Input',ThisOne='Fn_in'):
        Fn_in = cf['Climatology']['Fn_in']
    else:
        Fn_in = 'Fn'
    
    if qcutils.cfkeycheck(cf,Base='Input',ThisOne='Fg_in'):
        Fg_in = cf['Climatology']['Fg_in']
    else:
        Fg_in = 'Fg'
    
    if qcutils.cfkeycheck(cf,Base='Input',ThisOne='Fe_in'):
        Fe_in = cf['Climatology']['Fe_in']
    else:
        Fe_in = 'Fe'
    
    if qcutils.cfkeycheck(cf,Base='Input',ThisOne='Fh_in'):
        Fh_in = cf['Climatology']['Fh_in']
    else:
        Fh_in = 'Fh'
    
    if qcutils.cfkeycheck(cf,Base='Input',ThisOne='Fc_in'):
        Fc_in = cf['Climatology']['Fc_in']
    else:
        Fc_in = 'Fc'
    
    if qcutils.cfkeycheck(cf,Base='Params',ThisOne='firstMonth'):
        M1st = int(cf['Params']['firstMonth'])
    else:
        M1st = 1
    
    if qcutils.cfkeycheck(cf,Base='Params',ThisOne='secondMonth'):
        M2nd = int(cf['Params']['secondMonth'])
    else:
        M2nd = 12
    
    dt = int(ds.globalattributes['time_step'])
    xlFileName = cf['Files']['Climatology']['xlFilePath']+cf['Files']['Climatology']['xlFileName']
    xlFile = xlwt.Workbook()
    monthabr = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    Hdh,f = qcutils.GetSeriesasMA(ds,'Hdh')
    for ThisOne in OList:
        log.info('  Doing climatology for '+str(ThisOne))
        xlSheet = xlFile.add_sheet(ThisOne)
        xlCol = 0
        data,f = qcutils.GetSeriesasMA(ds,ThisOne)
        for month in range(M1st,M2nd+1):
            mi = numpy.where(ds.series['Month']['Data']==month)[0]
            Num,Hr,Av,Sd,Mx,Mn = qcutils.get_diurnalstats(Hdh[mi],data[mi],dt)
            Num = numpy.ma.filled(Num,float(-9999))
            Hr = numpy.ma.filled(Hr,float(-9999))
            if month==1:
                xlSheet.write(1,xlCol,'Hour')
                for j in range(len(Hr)):
                    xlSheet.write(j+2,xlCol,Hr[j])
                
                xlCol = xlCol + 1
            
            xlSheet.write(0,xlCol,monthabr[month-1])
            xlSheet.write(1,xlCol,'Num')
            xlSheet.write(1,xlCol+1,'Av')
            xlSheet.write(1,xlCol+2,'Sd')
            xlSheet.write(1,xlCol+3,'Mx')
            xlSheet.write(1,xlCol+4,'Mn')
            Av = numpy.ma.filled(Av,float(-9999))
            Sd = numpy.ma.filled(Sd,float(-9999))
            Mx = numpy.ma.filled(Mx,float(-9999))
            Mn = numpy.ma.filled(Mn,float(-9999))
            for j in range(len(Hr)):
                xlSheet.write(j+2,xlCol,Num[j])
                xlSheet.write(j+2,xlCol+1,Av[j])
                xlSheet.write(j+2,xlCol+2,Sd[j])
                xlSheet.write(j+2,xlCol+3,Mx[j])
                xlSheet.write(j+2,xlCol+4,Mn[j])
            
            xlCol = xlCol + 5
    
    if efflag != 'False':
        # calculate the evaporative fraction
        xlSheet = xlFile.add_sheet('EF')
        xlCol = 0
        EF = numpy.ma.zeros([48,12]) + float(-9999)
        log.info('  Doing evaporative fraction')
        for month in range(M1st,M2nd+1):
            mi = numpy.where((ds.series['Month']['Data']==month))[0]
            Hdh = numpy.ma.masked_where(abs(ds.series['Hdh']['Data'][mi]-float(-9999))<c.eps,
                                        ds.series['Hdh']['Data'][mi])
            Fn = numpy.ma.masked_where(abs(ds.series[Fn_in]['Data'][mi]-float(-9999))<c.eps,
                                       ds.series[Fn_in]['Data'][mi])
            Fg = numpy.ma.masked_where(abs(ds.series[Fg_in]['Data'][mi]-float(-9999))<c.eps,
                                       ds.series[Fg_in]['Data'][mi])
            Fa = Fn - Fg
            Fe = numpy.ma.masked_where(abs(ds.series[Fe_in]['Data'][mi]-float(-9999))<c.eps,
                                       ds.series[Fe_in]['Data'][mi])
            Fa_Num,Hr,Fa_Av,Sd,Mx,Mn = qcutils.get_diurnalstats(Hdh,Fa,dt)
            Fe_Num,Hr,Fe_Av,Sd,Mx,Mn = qcutils.get_diurnalstats(Hdh,Fe,dt)
            index = numpy.ma.where((Fa_Num>4)&(Fe_Num>4))
            EF[:,month-1][index] = Fe_Av[index]/Fa_Av[index]
        
        # reject EF values greater than or less than 1.5
        EF = numpy.ma.masked_where(abs(EF)>1.5,EF)
        EF = numpy.ma.filled(EF,float(-9999))
        # write the EF to the Excel object
        xlSheet.write(0,xlCol,'Hour')
        for j in range(len(Hr)):
            xlSheet.write(j+1,xlCol,Hr[j])
        xlCol = xlCol + 1
        d_xf = xlwt.easyxf(num_format_str='0.00')
        for month in range(M1st,M2nd+1):
            xlSheet.write(0,xlCol,monthabr[month-1])
            for j in range(len(Hr)):
                xlSheet.write(j+1,xlCol,EF[j,month-1],d_xf)
            xlCol = xlCol + 1
        # do the 2D interpolation to fill missing EF values
        EF_3x3=numpy.tile(EF,(3,3))
        nmn=numpy.shape(EF_3x3)[1]
        mni=numpy.arange(0,nmn)
        nhr=numpy.shape(EF_3x3)[0]
        hri=numpy.arange(0,nhr)
        mn,hr=numpy.meshgrid(mni,hri)
        EF_3x3_1d=numpy.reshape(EF_3x3,numpy.shape(EF_3x3)[0]*numpy.shape(EF_3x3)[1])
        mn_1d=numpy.reshape(mn,numpy.shape(mn)[0]*numpy.shape(mn)[1])
        hr_1d=numpy.reshape(hr,numpy.shape(hr)[0]*numpy.shape(hr)[1])
        index=numpy.where(EF_3x3_1d!=-9999)
        EF_3x3i=griddata(mn_1d[index],hr_1d[index],EF_3x3_1d[index],mni,hri)
        EFi=numpy.ma.filled(EF_3x3i[nhr/3:2*nhr/3,nmn/3:2*nmn/3],0)
        xlSheet = xlFile.add_sheet('EFi')
        xlCol = 0
        # write the interpolated EF values to the Excel object
        xlSheet.write(0,xlCol,'Hour')
        for j in range(len(Hr)):
            xlSheet.write(j+1,xlCol,Hr[j])
        xlCol = xlCol + 1
        d_xf = xlwt.easyxf(num_format_str='0.00')
        for month in range(M1st,M2nd+1):
            xlSheet.write(0,xlCol,monthabr[month-1])
            for j in range(len(Hr)):
                xlSheet.write(j+1,xlCol,EFi[j,month-1],d_xf)
            xlCol = xlCol + 1
    
    if brflag != 'False':
        # calculate the Bowen ratio
        xlSheet = xlFile.add_sheet('BR')
        xlCol = 0
        BR = numpy.ma.zeros([48,12]) + float(-9999)
        log.info('  Doing Bowen ratio')
        for month in range(M1st,M2nd+1):
            mi = numpy.where((ds.series['Month']['Data']==month))[0]
            Hdh = numpy.ma.masked_where(abs(ds.series['Hdh']['Data'][mi]-float(-9999))<c.eps,
                                        ds.series['Hdh']['Data'][mi])
            Fe = numpy.ma.masked_where(abs(ds.series[Fe_in]['Data'][mi]-float(-9999))<c.eps,
                                       ds.series[Fe_in]['Data'][mi])
            Fh = numpy.ma.masked_where(abs(ds.series[Fh_in]['Data'][mi]-float(-9999))<c.eps,
                                       ds.series[Fh_in]['Data'][mi])
            Fh_Num,Hr,Fh_Av,Sd,Mx,Mn = qcutils.get_diurnalstats(Hdh,Fh,dt)
            Fe_Num,Hr,Fe_Av,Sd,Mx,Mn = qcutils.get_diurnalstats(Hdh,Fe,dt)
            index = numpy.ma.where((Fh_Num>4)&(Fe_Num>4))
            BR[:,month-1][index] = Fh_Av[index]/Fe_Av[index]
        # reject BR values greater than or less than 5
        BR = numpy.ma.masked_where(abs(BR)>20.0,BR)
        BR = numpy.ma.filled(BR,float(-9999))
        # write the BR to the Excel object
        xlSheet.write(0,xlCol,'Hour')
        for j in range(len(Hr)):
            xlSheet.write(j+1,xlCol,Hr[j])
        xlCol = xlCol + 1
        d_xf = xlwt.easyxf(num_format_str='0.00')
        for month in range(M1st,M2nd+1):
            xlSheet.write(0,xlCol,monthabr[month-1])
            for j in range(len(Hr)):
                xlSheet.write(j+1,xlCol,BR[j,month-1],d_xf)
            xlCol = xlCol + 1
        # do the 2D interpolation to fill missing BR values
        # tile to 3,3 array so we have a patch in the centre, this helps
        # deal with edge effects
        BR_3x3=numpy.tile(BR,(3,3))
        nmn=numpy.shape(BR_3x3)[1]
        mni=numpy.arange(0,nmn)
        nhr=numpy.shape(BR_3x3)[0]
        hri=numpy.arange(0,nhr)
        mn,hr=numpy.meshgrid(mni,hri)
        BR_3x3_1d=numpy.reshape(BR_3x3,numpy.shape(BR_3x3)[0]*numpy.shape(BR_3x3)[1])
        mn_1d=numpy.reshape(mn,numpy.shape(mn)[0]*numpy.shape(mn)[1])
        hr_1d=numpy.reshape(hr,numpy.shape(hr)[0]*numpy.shape(hr)[1])
        index=numpy.where(BR_3x3_1d!=-9999)
        BR_3x3i=griddata(mn_1d[index],hr_1d[index],BR_3x3_1d[index],mni,hri)
        BRi=numpy.ma.filled(BR_3x3i[nhr/3:2*nhr/3,nmn/3:2*nmn/3],0)
        xlSheet = xlFile.add_sheet('BRi')
        xlCol = 0
        # write the interpolated BR values to the Excel object
        xlSheet.write(0,xlCol,'Hour')
        for j in range(len(Hr)):
            xlSheet.write(j+1,xlCol,Hr[j])
        xlCol = xlCol + 1
        d_xf = xlwt.easyxf(num_format_str='0.00')
        for month in range(M1st,M2nd+1):
            xlSheet.write(0,xlCol,monthabr[month-1])
            for j in range(len(Hr)):
                xlSheet.write(j+1,xlCol,BRi[j,month-1],d_xf)
            xlCol = xlCol + 1
    
    if wueflag != 'False':
        # calculate the ecosystem water use efficiency
        xlSheet = xlFile.add_sheet('WUE')
        xlCol = 0
        WUE = numpy.ma.zeros([48,12]) + float(-9999)
        log.info('  Doing ecosystem WUE')
        for month in range(M1st,M2nd+1):
            mi = numpy.where((ds.series['Month']['Data']==month))[0]
            Hdh = numpy.ma.masked_where(abs(ds.series['Hdh']['Data'][mi]-float(-9999))<c.eps,
                                        ds.series['Hdh']['Data'][mi])
            Fe = numpy.ma.masked_where(abs(ds.series[Fe_in]['Data'][mi]-float(-9999))<c.eps,
                                       ds.series[Fe_in]['Data'][mi])
            Fc = numpy.ma.masked_where(abs(ds.series[Fc_in]['Data'][mi]-float(-9999))<c.eps,
                                       ds.series[Fc_in]['Data'][mi])
            Fc_Num,Hr,Fc_Av,Sd,Mx,Mn = qcutils.get_diurnalstats(Hdh,Fc,dt)
            Fe_Num,Hr,Fe_Av,Sd,Mx,Mn = qcutils.get_diurnalstats(Hdh,Fe,dt)
            index = numpy.ma.where((Fc_Num>4)&(Fe_Num>4))
            WUE[:,month-1][index] = Fc_Av[index]/Fe_Av[index]
        # reject WUE values greater than 0.04 or less than -0.004
        WUE = numpy.ma.masked_where((WUE>0.04)|(WUE<-0.004),WUE)
        WUE = numpy.ma.filled(WUE,float(-9999))
        # write the WUE to the Excel object
        xlSheet.write(0,xlCol,'Hour')
        for j in range(len(Hr)):
            xlSheet.write(j+1,xlCol,Hr[j])
        xlCol = xlCol + 1
        d_xf = xlwt.easyxf(num_format_str='0.00000')
        for month in range(M1st,M2nd+1):
            xlSheet.write(0,xlCol,monthabr[month-1])
            for j in range(len(Hr)):
                xlSheet.write(j+1,xlCol,WUE[j,month-1],d_xf)
            xlCol = xlCol + 1
        # do the 2D interpolation to fill missing WUE values
        WUE_3x3=numpy.tile(WUE,(3,3))
        nmn=numpy.shape(WUE_3x3)[1]
        mni=numpy.arange(0,nmn)
        nhr=numpy.shape(WUE_3x3)[0]
        hri=numpy.arange(0,nhr)
        mn,hr=numpy.meshgrid(mni,hri)
        WUE_3x3_1d=numpy.reshape(WUE_3x3,numpy.shape(WUE_3x3)[0]*numpy.shape(WUE_3x3)[1])
        mn_1d=numpy.reshape(mn,numpy.shape(mn)[0]*numpy.shape(mn)[1])
        hr_1d=numpy.reshape(hr,numpy.shape(hr)[0]*numpy.shape(hr)[1])
        index=numpy.where(WUE_3x3_1d!=-9999)
        WUE_3x3i=griddata(mn_1d[index],hr_1d[index],WUE_3x3_1d[index],mni,hri)
        WUEi=numpy.ma.filled(WUE_3x3i[nhr/3:2*nhr/3,nmn/3:2*nmn/3],0)
        xlSheet = xlFile.add_sheet('WUEi')
        xlCol = 0
        # write the interpolated WUE values to the Excel object
        xlSheet.write(0,xlCol,'Hour')
        for j in range(len(Hr)):
            xlSheet.write(j+1,xlCol,Hr[j])
        xlCol = xlCol + 1
        d_xf = xlwt.easyxf(num_format_str='0.00000')
        for month in range(M1st,M2nd+1):
            xlSheet.write(0,xlCol,monthabr[month-1])
            for j in range(len(Hr)):
                xlSheet.write(j+1,xlCol,WUEi[j,month-1],d_xf)
            xlCol = xlCol + 1
    
    log.info('  Saving Excel file '+str(xlFileName))
    xlFile.save(xlFileName)
    
    log.info(' Climatology: All done')

def ComputeDailySums(cf,ds,SumList,SubSumList,MinMaxList,MeanList,SoilList):
    """
        Computes daily sums, mininima and maxima on a collection variables in
        the L4 dataset containing gap filled fluxes.  Sums are computed only
        when the number of daily 30-min observations is equal to 48 (i.e., no
        missing data) to avoid biasing.  Output to an excel file that specified
        in the control file.
        
        Usage qcts.ComputeDailySums(cf,ds)
        cf: control file
        ds: data structure
        
        Parameters loaded from control file:
            M1st: dataset start month
            M2nd: dataset end month
            SumList: list of variables to be summed
            SubSumList: list of variables to sum positive and negative observations separately
            MinMaxList: list of variables to compute daily min & max
            SoilList: list of soil moisture measurements groups
            SW0, SW10, etc: list of soil moisture sensors at a common level (e.g., surface, 10cm, etc)
        
        Default List of sums:
            Rain, ET, Fe_MJ, Fh_MJ, Fg_MJ, Fld_MJ, Flu_MJ, Fn_MJ, Fsd_MJ,
            Fsu_MJ, Fc_g, Fc_mmol
        Default List of sub-sums (sums split between positive and negative observations)
            Fe_MJ, Fh_MJ, Fg_MJ
        Default List of min/max:
            Ta_HMP, Vbat, Tpanel, Fc_mg, Fc_umol
        Default List of soil moisture measurements:
        """
    OutList = []
    SumOutList = []
    SubOutList = []
    MinMaxOutList = []
    MeanOutList = []
    SoilOutList = []
    
    for ThisOne in SubSumList:
        if ThisOne not in SumList:
            SumList.append(ThisOne)
    
    for ThisOne in SumList:
        if ThisOne == 'ET':
            if 'ET' not in ds.series.keys():
                if qcutils.cfkeycheck(cf,Base='CalculateET',ThisOne='Fe_in'):
                    Fe_in = cf['Sums']['Fe_in']
                else:
                    Fe_in = 'Fe'
                Fe,f = qcutils.GetSeriesasMA(ds,Fe_in)
                if 'Lv' in ds.series.keys():
                    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
                else:
                    Lv = c.Lv
                ET = Fe * 60 * 30 * 1000 / (Lv * c.rho_water)  # mm/30min for summing
                qcutils.CreateSeries(ds,'ET',ET,FList=[Fe_in],Descr='Evapotranspiration Flux',Units='mm/30min')
            
            SumOutList.append('ET')
            OutList.append('ET')
            if ThisOne in SubSumList:
                SubOutList.append('ET')
        elif ThisOne == 'Energy':
            if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='Energyin'):
                EnergyIn = ast.literal_eval(cf['Sums']['Energyin'])
            else:
                EnergyIn = ['Fe', 'Fh', 'Fg']
            Fe,f = qcutils.GetSeriesasMA(ds,EnergyIn[0])
            Fh,f = qcutils.GetSeriesasMA(ds,EnergyIn[1])
            Fg,f = qcutils.GetSeriesasMA(ds,EnergyIn[2])
            EnergyOut = ['Fe_MJ','Fh_MJ','Fg_MJ']
            for index in range(0,3):
                convert_energy(ds,EnergyIn[index],EnergyOut[index])
                OutList.append(EnergyOut[index])
                SumOutList.append(EnergyOut[index])
                if ThisOne in SubSumList:
                    SubOutList.append(EnergyOut[index])
        elif ThisOne == 'Radiation':
            if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='Radin'):
                RadiationIn = ast.literal_eval(cf['Sums']['Radin'])
            else:
                RadiationIn = ['Fld','Flu','Fn','Fsd','Fsu']
            Fld,f = qcutils.GetSeriesasMA(ds,RadiationIn[0])
            Flu,f = qcutils.GetSeriesasMA(ds,RadiationIn[1])
            Fn,f = qcutils.GetSeriesasMA(ds,RadiationIn[2])
            Fsd,f = qcutils.GetSeriesasMA(ds,RadiationIn[3])
            Fsu,f = qcutils.GetSeriesasMA(ds,RadiationIn[4])
            RadiationOut = ['Fld_MJ','Flu_MJ','Fn_MJ','Fsd_MJ','Fsu_MJ']
            for index in range(0,5):
                convert_energy(ds,RadiationIn[index],RadiationOut[index])
                OutList.append(RadiationOut[index])
                SumOutList.append(RadiationOut[index])
                if ThisOne in SubSumList:
                    log.error('  Subsum: Negative radiation flux not defined')
        elif ThisOne == 'Carbon':
            if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='Cin'):
                CIn = cf['Sums']['Cin']
            else:
                CIn = 'Fc'
            
            if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='GPPin'):
                GPPIn = ast.literal_eval(cf['Sums']['GPPin'])
                GPP,f = qcutils.GetSeriesasMA(ds,GPPIn[0])
                Re,f = qcutils.GetSeriesasMA(ds,GPPIn[1])
                Fsd,f = qcutils.GetSeriesasMA(ds,'Fsd')
                GPP_mmol = GPP * 1800 / 1000
                Re_mmol = Re * 1800 / 1000
                Re_LRF_mmol = numpy.zeros(len(Re_mmol), float) + Re_mmol
                Re_n_mmol = numpy.zeros(len(Re_mmol), float)
                Re_NEEmax_mmol = numpy.zeros(len(Re_mmol), float)
                nightindex = numpy.where(Fsd < 10)[0]
                NEEmaxindex = numpy.where(Fsd > 500)[0]
                Re_LRF_mmol[nightindex] = 0.
                Re_LRF_mmol[NEEmaxindex] = 0.
                Re_n_mmol[nightindex] = Re_mmol[nightindex]
                Re_NEEmax_mmol[NEEmaxindex] = Re_mmol[NEEmaxindex]
                qcutils.CreateSeries(ds,'GPP_mmol',GPP_mmol,FList=[GPPIn[0]],Descr='Cumulative 30-min GPP',Units='mmol/m2',Standard='gross_primary_productivity_of_carbon')
                qcutils.CreateSeries(ds,'Re_mmol',Re_mmol,FList=[GPPIn[1]],Descr='Cumulative 30-min Re',Units='mmol/m2')
                qcutils.CreateSeries(ds,'Re_LRF_mmol',Re_LRF_mmol,FList=[GPPIn[1]],Descr='Cumulative 30-min Re, estimated by LRF',Units='mmol/m2')
                qcutils.CreateSeries(ds,'Re_n_mmol',Re_n_mmol,FList=[GPPIn[1]],Descr='Cumulative 30-min Re, nocturnal accumulation',Units='mmol/m2')
                qcutils.CreateSeries(ds,'Re_NEEmax_mmol',Re_NEEmax_mmol,FList=[GPPIn[1]],Descr='Cumulative 30-min Re, estimated by LRF',Units='mmol/m2')
                GPPOut = ['GPP_mmol','Re_mmol','Re_LRF_mmol','Re_n_mmol','Re_NEEmax_mmol']
                for listindex in range(0,5):
                    OutList.append(GPPOut[listindex])
                    SumOutList.append(GPPOut[listindex])
            
            Fc,f = qcutils.GetSeriesasMA(ds,CIn)
            Fc_umol = Fc * 1e6 / (1000 * 44)               # umol/m2-s for min/max
            Fc_mmol = Fc_umol * 1800 / 1000                # mmol/m2-30min for summing
            Fc_g = Fc * 1800 / 1000                        # g/m2-30min for summing
            qcutils.CreateSeries(ds,'Fc_mmol',Fc_mmol,FList=[CIn],Descr='Cumulative 30-min Flux',Units='mmol/m2',Standard='surface_upward_mole_flux_of_carbon_dioxide')
            qcutils.CreateSeries(ds,'Fc_g',Fc_g,FList=[CIn],Descr='Cumulative 30-min Flux',Units='g/m2')
            COut = ['Fc_g','Fc_mmol']
            for listindex in range(0,2):
                OutList.append(COut[listindex])
                SumOutList.append(COut[listindex])
                if ThisOne in SubSumList:
                    SubOutList.append(COut[listindex])
        elif ThisOne == 'PM':
            if 'GE_2layer' not in ds.series.keys() and 'GE_1layer' not in ds.series.keys() and 'GC' not in ds.series.keys():
                SumList.remove('PM')
                log.error('  Penman-Monteith Daily sum: input Gst or Gc not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cemethod') and cf['PenmanMonteith']['Cemethod'] == 'True':
                if 'GE_1layer' in ds.series.keys():
                    Gst_1layer_mmol,f = qcutils.GetSeriesasMA(ds,'GE_1layer')   # mmol/m2-s
                    Gst_1layer_mol =  Gst_1layer_mmol * 1800 / 1000                 # mol/m2-30min for summing
                    qcutils.CreateSeries(ds,'GE_1layer_mol',Gst_1layer_mol,FList=['GE_1layer'],Descr='Cumulative 30-min Bulk Stomatal Conductance, 1-layer Ce method Penman-Monteith',Units='mol/m2')
                    OutList.append('GE_1layer_mol')
                    if 'GE_1layer_mol' in SubSumList:
                        log.error('  Subsum: Negative bulk stomatal conductance not defined')
                    SumOutList.append('GE_1layer_mol')
                else:
                    log.error('  Penman-Monteith Daily sum: input Gst_1layer not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Ce_2layer') and cf['PenmanMonteith']['Ce_2layer'] == 'True':
                if 'GE_2layer' in ds.series.keys() and 'GE_top' in ds.series.keys() and 'GE_base' in ds.series.keys() and 'GE_full' in ds.series.keys():
                    for ThisOne in ['GE_2layer','GE_top','GE_base','GE_full']:
                        Gst_2layer_mmol,f = qcutils.GetSeriesasMA(ds,ThisOne)   # mmol/m2-s
                        Gst_2layer_mol =  Gst_2layer_mmol * 1800 / 1000                 # mol/m2-30min for summing
                        newvar = ThisOne + '_mol'
                        qcutils.CreateSeries(ds,newvar,Gst_2layer_mol,FList=[ThisOne],Descr='Cumulative 30-min Bulk Stomatal Conductance, 2-layer Ce method Penman-Monteith',Units='mol/m2')
                        OutList.append(newvar)
                        if newvar in SubSumList:
                            log.error('  Subsum: Negative bulk stomatal conductance not defined')
                        SumOutList.append(newvar)
                else:
                    log.error('  Penman-Monteith Daily sum: input Gst_2layer not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cdmethod') and cf['PenmanMonteith']['Cdmethod'] == 'True':
                if 'GC' in ds.series.keys():
                    Gc_mmol,f = qcutils.GetSeriesasMA(ds,'GC')   # mmol/m2-s
                    Gc_mol =  Gc_mmol * 1800 / 1000                 # mol/m2-30min for summing
                    qcutils.CreateSeries(ds,'GC_mol',Gc_mol,FList=['GC'],Descr='Cumulative 30-min Canopy Conductance',Units='mol/m2')
                    OutList.append('GC_mol')
                    if 'GC_mol' in SubSumList:
                        log.error('  Subsum: Negative bulk stomatal conductance not defined')
                    SumOutList.append('GC_mol')
                else:
                    log.error('  Penman-Monteith Daily sum: input Gc not located')
        elif ThisOne == 'Rainhours':
            rain,f = qcutils.GetSeriesasMA(ds,'Rain')
            day,f = qcutils.GetSeriesasMA(ds,'Ddd')
            rainhr = numpy.zeros(len(day), dtype=float)
            for i in range(int(numpy.floor(day[0])),int(numpy.floor(day[-1]))):
                index = numpy.where(((day - i) < 1) & (((day - i) > 0) | ((day - i) == 0)))[0]
                for j in range(len(index)):
                    if rain[index[j]] > 0:
                        rainhr[index[j]] = 0.5
            qcutils.CreateSeries(ds,'rainhrs',rainhr,FList=['Rain'],Descr='Hourly rainfall occurrence (1) or absence (0)')
            OutList.append('rainhrs')
            SumOutList.append('rainhrs')
        else:
            OutList.append(ThisOne)
            SumOutList.append(ThisOne)
    
    for ThisOne in MinMaxList:
        if ThisOne == 'Carbon':
            if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='Cin'):
                CIn = cf['Sums']['Cin']
            else:
                CIn = 'Fc'
            Fc,f = qcutils.GetSeriesasMA(ds,CIn)
            Fc_umol = Fc * 1e6 / (1000 * 44)               # umol/m2-s for min/max
            qcutils.CreateSeries(ds,'Fc_umol',Fc_umol,FList=[CIn],Descr='Average Flux',Units='umol/(m2 s)',Standard='surface_upward_mole_flux_of_carbon_dioxide')
            qcutils.CreateSeries(ds,'Fc_mg',Fc,FList=[CIn],Descr='Average Flux',Units='mg/(m2 s)')
            COut = ['Fc_mg','Fc_umol']
            for listindex in range(0,2):
                OutList.append(COut[listindex])
                MinMaxOutList.append(COut[listindex])
        elif ThisOne == 'PM':
            if 'GE_1layer' not in ds.series.keys() and 'GE_2layer' not in ds.series.keys() and 'GE_base' not in ds.series.keys() and 'GE_top' not in ds.series.keys() and 'GC' not in ds.series.keys() and 'rE_1layer' not in ds.series.keys() and 'rE_2layer' not in ds.series.keys() and 'rE_base' not in ds.series.keys() and 'rE_top' not in ds.series.keys() and 'rC' not in ds.series.keys() and 'rav_1layer' not in ds.series.keys() and 'rav_2layer' not in ds.series.keys() and 'rav_base' not in ds.series.keys() and 'rav_top' not in ds.series.keys() and 'ram' not in ds.series.keys():
                MinMaxList.remove('PM')
                log.error('  Penman-Monteith Daily min/max: input Gst, rst, rc or Gc not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cemethod') and cf['PenmanMonteith']['Cemethod'] == 'True':
                if 'GE_1layer' in ds.series.keys() and 'rE_1layer' in ds.series.keys():
                    PMout = ['rE_1layer','GE_1layer']
                    for listindex in range(0,2):
                        if PMout[listindex] not in OutList:
                            OutList.append(PMout[listindex])
                        MinMaxOutList.append(PMout[listindex])
                else:
                    log.error('  Penman-Monteith Daily min/max: input Gst_1layer or rst_1layer not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Ce_2layer') and cf['PenmanMonteith']['Ce_2layer'] == 'True':
                if 'rav_2layer' in ds.series.keys() and 'GE_2layer' in ds.series.keys() and 'rE_2layer' in ds.series.keys() and 'rav_base' in ds.series.keys() and 'GE_base' in ds.series.keys() and 'rE_base' in ds.series.keys() and 'rav_top' in ds.series.keys() and 'GE_top' in ds.series.keys() and 'rE_top' in ds.series.keys() and 'rav_full' in ds.series.keys() and 'GE_full' in ds.series.keys() and 'rE_full' in ds.series.keys():
                    PMout = ['rav_2layer','rE_2layer','GE_2layer','rav_base','rE_base','GE_base','rav_top','rE_top','GE_top','rav_full','rE_full','GE_full']
                    for listindex in range(0,12):
                        if PMout[listindex] not in OutList:
                            OutList.append(PMout[listindex])
                        MinMaxOutList.append(PMout[listindex])
                else:
                    log.error('  Penman-Monteith Daily mean: input rav_2layer, Gst_2layer, rst_2layer, rav_base, Gst_base, rst_base, rav_top, Gst_top, rst_full, rav_full, Gst_full or rst_full not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cdmethod') and cf['PenmanMonteith']['Cdmethod'] == 'True':
                if 'GC' in ds.series.keys() and 'rC' in ds.series.keys():
                    PMout = ['ram','rC','GC']
                    for listindex in range(0,3):
                        if PMout[listindex] not in OutList:
                            OutList.append(PMout[listindex])
                        MinMaxOutList.append(PMout[listindex])
                else:
                    log.error('  Penman-Monteith Daily min/max: input Gc or rc not located')
        else:
            if ThisOne not in OutList:
                OutList.append(ThisOne)
            MinMaxOutList.append(ThisOne)
    
    for ThisOne in MeanList:
        if ThisOne == 'Energy' or ThisOne == 'Carbon' or ThisOne == 'Radiation':
            log.error(' Mean error: '+ThisOne+' to be placed in SumList')
        elif ThisOne == 'PM':
            if 'GE_1layer' not in ds.series.keys() and 'GE_2layer' not in ds.series.keys() and 'GE_base' not in ds.series.keys() and 'GE_top' not in ds.series.keys() and 'GC' not in ds.series.keys() and 'rE_1layer' not in ds.series.keys() and 'rE_2layer' not in ds.series.keys() and 'rE_base' not in ds.series.keys() and 'rE_top' not in ds.series.keys() and 'rC' not in ds.series.keys() and 'rav_1layer' not in ds.series.keys() and 'rav_2layer' not in ds.series.keys() and 'rav_base' not in ds.series.keys() and 'rav_top' not in ds.series.keys() and 'ram' not in ds.series.keys():
                MeanList.remove('PM')
                log.error('  Penman-Monteith Daily mean: input Gst, rst, rc or Gc not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cemethod') and cf['PenmanMonteith']['Cemethod'] == 'True':
                if 'GE_1layer' in ds.series.keys() and 'rE_1layer' in ds.series.keys():
                    PMout = ['rE_1layer','GE_1layer']
                    for listindex in range(0,2):
                        if PMout[listindex] not in OutList:
                            OutList.append(PMout[listindex])
                        MeanOutList.append(PMout[listindex])
                else:
                    log.error('  Penman-Monteith Daily mean: input Gst_1layer or rst_1layer not located')
                
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Ce_2layer') and cf['PenmanMonteith']['Ce_2layer'] == 'True':
                if 'rav_2layer' in ds.series.keys() and 'GE_2layer' in ds.series.keys() and 'rE_2layer' in ds.series.keys() and 'rav_base' in ds.series.keys() and 'GE_base' in ds.series.keys() and 'rE_base' in ds.series.keys() and 'rav_top' in ds.series.keys() and 'GE_top' in ds.series.keys() and 'rE_top' in ds.series.keys() and 'rav_full' in ds.series.keys() and 'GE_full' in ds.series.keys() and 'rE_full' in ds.series.keys():
                    PMout = ['rav_2layer','rE_2layer','GE_2layer','rav_base','rE_base','GE_base','rav_top','rE_top','GE_top','rav_full','rE_full','GE_full']
                    for listindex in range(0,12):
                        if PMout[listindex] not in OutList:
                            OutList.append(PMout[listindex])
                        MeanOutList.append(PMout[listindex])
                else:
                    log.error('  Penman-Monteith Daily mean: input rav_2layer, Gst_2layer, rst_2layer, rav_base, Gst_base, rst_base, rav_top, Gst_top or rst_top not located')
            
            if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cdmethod') and cf['PenmanMonteith']['Cdmethod'] == 'True':
                if 'GC' in ds.series.keys() and 'rC' in ds.series.keys():
                    PMout = ['ram','rC','GC']
                    for listindex in range(0,3):
                        if PMout[listindex] not in OutList:
                            OutList.append(PMout[listindex])
                        MeanOutList.append(PMout[listindex])
                else:
                    log.error('  Penman-Monteith Daily mean: input Gc or rc not located')
        else:
            MeanOutList.append(ThisOne)
            if ThisOne not in OutList:
                OutList.append(ThisOne)
    
    if len(SoilList) > 0:
        for ThisOne in SoilList:
            if qcutils.cfkeycheck(cf,Base='Sums',ThisOne=ThisOne):
                vars = ast.literal_eval(cf['Sums'][ThisOne])
                for index in range(0,len(vars)):
                    SoilOutList.append(vars[index])
                OutList.append(ThisOne)
    
    xlFileName = cf['Files']['L4']['xlSumFilePath']+cf['Files']['L4']['xlSumFileName']
    xlFile = xlwt.Workbook()
    
    for ThisOne in OutList:
        xlSheet = xlFile.add_sheet(ThisOne)
        xlCol = 0
        if ThisOne in SumOutList:
            if ThisOne in SubOutList:
                write_sums(cf,ds,ThisOne,xlCol,xlSheet,DoSum='True',DoSubSum='True')
            else:
                write_sums(cf,ds,ThisOne,xlCol,xlSheet,DoSum='True')
        
        if ThisOne in MinMaxOutList:
            if ThisOne in MeanOutList:
                write_sums(cf,ds,ThisOne,xlCol,xlSheet,DoMinMax='True',DoMean='True')
            else:
                write_sums(cf,ds,ThisOne,xlCol,xlSheet,DoMinMax='True')
        
        if ThisOne in MeanOutList:
            if ThisOne not in MinMaxOutList:
                write_sums(cf,ds,ThisOne,xlCol,xlSheet,DoMean='True')
        
        if ThisOne in SoilList:
            soilvars = ast.literal_eval(cf['Sums'][ThisOne])
            for n in soilvars:
                if n == soilvars[0]:
                    xC,xS = write_sums(cf,ds,n,xlCol,xlSheet,DoSoil='True')
                else:
                    xC,xS = write_sums(cf,ds,n,xlCol,xS,DoSoil='True')
                xlCol = xC + 1
        
    log.info(' Saving Excel file '+xlFileName)
    xlFile.save(xlFileName)

    log.info(' Daily sums: All done')

def convert_energy(ds,InVar,OutVar):
    """
        Integrate energy flux over 30-min time period.
        Converts flux in W/m2 to MJ/(m2 30-min)
        
        Usage qcts.convert_energy(ds,InVar,OutVar)
        ds: data structure
        InVar: name of input variable.  Example: 'Fe_gapfilled'
        OutVar: name of output variable.  Example: 'Fe_MJ'
        """
    Wm2,f = qcutils.GetSeriesasMA(ds,InVar)
    MJ = Wm2 * 1800 / 1e6
    qcutils.CreateSeries(ds,OutVar,MJ,FList=[InVar],Descr=ds.series[InVar]['Attr']['long_name'],Units='MJ/m2',Standard=ds.series[InVar]['Attr']['standard_name'])

def CoordRotation2D(cf,ds):
    """
        2D coordinate rotation to force v = w = 0.  Based on Lee et al, Chapter
        3 of Handbook of Micrometeorology.  This routine does not do the third
        rotation to force v'w' = 0.
        
        Usage qcts.CoordRotation2D(ds)
        ds: data structure
        """
    log.info(' Applying 2D coordinate rotation to wind components and covariances')
    # get the raw wind velocity components
    Ux,f = qcutils.GetSeriesasMA(ds,'Ux')          # longitudinal component in CSAT coordinate system
    Uy,f = qcutils.GetSeriesasMA(ds,'Uy')          # lateral component in CSAT coordinate system
    Uz,f = qcutils.GetSeriesasMA(ds,'Uz')          # vertical component in CSAT coordinate system
    # get the raw covariances
    UxUz,f = qcutils.GetSeriesasMA(ds,'UxUz')      # covariance(Ux,Uz)
    UyUz,f = qcutils.GetSeriesasMA(ds,'UyUz')      # covariance(Uy,Uz)
    UxUy,f = qcutils.GetSeriesasMA(ds,'UxUy')      # covariance(Ux,Uy)
    UyUy,f = qcutils.GetSeriesasMA(ds,'UyUy')      # variance(Uy)
    UxUx,f = qcutils.GetSeriesasMA(ds,'UxUx')      # variance(Ux)
    UzC,f = qcutils.GetSeriesasMA(ds,'UzC')        # covariance(Uz,C)
    UzA,f = qcutils.GetSeriesasMA(ds,'UzA')        # covariance(Uz,A)
    UzT,f = qcutils.GetSeriesasMA(ds,'UzT')        # covariance(Uz,T)
    UxC,f = qcutils.GetSeriesasMA(ds,'UxC')        # covariance(Ux,C)
    UyC,f = qcutils.GetSeriesasMA(ds,'UyC')        # covariance(Uy,C)
    UxA,f = qcutils.GetSeriesasMA(ds,'UxA')        # covariance(Ux,A)
    UyA,f = qcutils.GetSeriesasMA(ds,'UyA')        # covariance(Ux,A)
    UxT,f = qcutils.GetSeriesasMA(ds,'UxT')        # covariance(Ux,T)
    UyT,f = qcutils.GetSeriesasMA(ds,'UyT')        # covariance(Uy,T)
    nRecs = len(Ux)
    # get the 2D and 3D wind speeds
    ws2d = numpy.ma.sqrt(Ux**2 + Uy**2)
    ws3d = numpy.ma.sqrt(Ux**2 + Uy**2 + Uz**2)
    # get the sine and cosine of the angles through which to rotate
    #  - first we rotate about the Uz axis by eta to get v = 0
    #  - then we rotate about the v axis by theta to get w = 0
    ce = Ux/ws2d          # cos(eta)
    se = Uy/ws2d          # sin(eta)
    ct = ws2d/ws3d        # cos(theta)
    st = Uz/ws3d          # sin(theta)
    # get the rotation angles
    theta = numpy.rad2deg(numpy.arctan2(st,ct))
    eta = numpy.rad2deg(numpy.arctan2(se,ce))
    # do the wind velocity components first
    u = Ux*ct*ce + Uy*ct*se + Uz*st           # longitudinal component in natural wind coordinates
    v = Uy*ce - Ux*se                         # lateral component in natural wind coordinates
    w = Uz*ct - Ux*st*ce - Uy*st*se           # vertical component in natural wind coordinates
    # now do the covariances
    wT = UzT*ct - UxT*st*ce - UyT*st*se       # covariance(w,T) in natural wind coordinate system
    wA = UzA*ct - UxA*st*ce - UyA*st*se       # covariance(w,A) in natural wind coordinate system
    wC = UzC*ct - UxC*st*ce - UyC*st*se       # covariance(w,C) in natural wind coordinate system
    uw = UxUz*ct - UxUx*st*ce - UxUy*st*se    # covariance(w,x) in natural wind coordinate system
    vw = UyUz*ct - UxUy*st*ce - UyUy*st*se    # covariance(w,y) in natural wind coordinate system
    # store the rotated quantities in the nc object
    qcutils.CreateSeries(ds,'eta',eta,FList=['Ux','Uy','Uz'],Descr='Horizontal rotation angle',Units='deg')
    qcutils.CreateSeries(ds,'theta',theta,FList=['Ux','Uy','Uz'],Descr='Vertical rotation angle',Units='deg')
    qcutils.CreateSeries(ds,'u',u,FList=['Ux','Uy','Uz'],Descr='Longitudinal component of wind-speed in natural wind coordinates',Units='m/s')
    qcutils.CreateSeries(ds,'v',v,FList=['Ux','Uy','Uz'],Descr='Lateral component of wind-speed in natural wind coordinates',Units='m/s')
    qcutils.CreateSeries(ds,'w',w,FList=['Ux','Uy','Uz'],Descr='Vertical component of wind-speed in natural wind coordinates',Units='m/s')
    qcutils.CreateSeries(ds,'wT',wT,FList=['Ux','Uy','Uz','UxT','UyT','UzT'],
                         Descr='Kinematic heat flux, rotated to natural wind coordinates',Units='mC/s')
    qcutils.CreateSeries(ds,'wA',wA,FList=['Ux','Uy','Uz','UxA','UyA','UzA'],
                         Descr='Kinematic vapour flux, rotated to natural wind coordinates',Units='g/m2/s')
    qcutils.CreateSeries(ds,'wC',wC,FList=['Ux','Uy','Uz','UxC','UyC','UzC'],
                         Descr='Kinematic CO2 flux, rotated to natural wind coordinates',Units='mg/m2/s')
    qcutils.CreateSeries(ds,'uw',uw,FList=['Ux','Uy','Uz','UxUz','UxUx','UxUy'],
                         Descr='Momentum flux X component, corrected to natural wind coordinates',Units='m2/s2')
    qcutils.CreateSeries(ds,'vw',vw,FList=['Ux','Uy','Uz','UyUz','UxUy','UyUy'],
                         Descr='Momentum flux Y component, corrected to natural wind coordinates',Units='m2/s2')
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='RotateFlag') and cf['General']['RotateFlag'] == 'True':
        keys = ['eta','theta','u','v','w','wT','wA','wC','uw','vw']
        for ThisOne in keys:
            testseries,f = qcutils.GetSeriesasMA(ds,ThisOne)
            mask = numpy.ma.getmask(testseries)
            index = numpy.where(mask.astype(int)==1)
            ds.series[ThisOne]['Flag'][index] = 11
    else:
        keys = ['eta','theta','u','v','w','wT','wA','wC','uw','vw']
        for ThisOne in keys:
            testseries,f = qcutils.GetSeriesasMA(ds,ThisOne)
            mask = numpy.ma.getmask(testseries)
            index = numpy.where((numpy.mod(f,10)==0) & (mask.astype(int)==1))    # find the elements with flag = 0, 10, 20 etc and masked (check for masked data with good data flag)
            ds.series[ThisOne]['Flag'][index] = 11

def ConvertFc(cf,ds,Fc_in='Fc'):
    """
    Converts CO2 flux (Fc) [mg m-2 s-1] to metabolic units [umol m-2 s-1]
    Calculates NEE [umol m-2 s-1] and NEP
    Fc = NEE = -NEP
    """
    log.info(' Converting Fc units')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='convertFc'):
        Fc_list = ast.literal_eval(cf['FunctionArgs']['convertFc'])
        Fc_in = Fc_list[0]
    Fc,f = qcutils.GetSeriesasMA(ds,Fc_in)
    NEE = Fc * 1e6 / (1000 * 44)
    NEP = -NEE
    qcutils.CreateSeries(ds,'NEE',NEE,FList=[Fc_in],Descr='NEE (Net ecosystem exchange of carbon), rotated to natural wind coordinates, frequency response corrected, and density flux corrected (wpl)',Units='umol/m2/s')
    qcutils.CreateSeries(ds,'NEP',NEP,FList=[Fc_in],Descr='NEP (Net ecosystem photosynthesis), rotated to natural wind coordinates, frequency response corrected, and density flux corrected (wpl)',Units='umol/m2/s')

def CorrectFcForStorage(cf,ds,Fc_out,Fc_in,CO2_in):
    """
    Correct CO2 flux for storage in the air column beneath the CO2 instrument.  This
    routine assumes the air column between the sensor and the surface is well mixed.
    
    Usage qcts.CorrectFcForStorage(cf,ds,Fc_out,Fc_in,CO2_in)
    cf: control file object    
    ds: data structure
    Fc_out: series label of the corrected CO2 flux
    Fc_in: series label of the uncorrected CO2 flux
    CO2_in: series label of the CO2 concentration
    
    Parameters loaded from control file:
        zm: measurement height, m
        dt: timestep, seconds
    """
    log.info(' Correcting Fc for storage')
    if 'General' in cf:
        if 'zms' in cf['General']:
            zms = float(cf['General']['zms'])
            Cc,Cc_flag = qcutils.GetSeriesasMA(ds,CO2_in,si=0,ei=-1)
            rhod,rhod_flag = qcutils.GetSeriesasMA(ds,'rhod',si=0,ei=-1)
            Fc,Fc_flag = qcutils.GetSeriesasMA(ds,Fc_in,si=0,ei=-1)
            dc = numpy.ma.ediff1d(Cc,to_begin=0)                      # CO2 concentration difference from timestep to timestep
            dt=86400*numpy.ediff1d(ds.series['xlDateTime']['Data'],to_begin=float(30)/1440)    # time step in seconds from the Excel datetime values
            Fc_storage = zms*rhod*dc/dt                               # calculate the CO2 flux based on storage below the measurement height
            descr = 'Fc infered from CO2 storage using single point CO2 measurement'
            units = qcutils.GetUnitsFromds(ds,Fc_in)
            qcutils.CreateSeries(ds,'Fc_storage',Fc_storage,FList=[Fc_in,CO2_in],Descr=descr,Units=units)
            Fc = Fc + Fc_storage
            descr = 'Fc_wpl corrected for storage using single point CO2 measurement'
            qcutils.CreateSeries(ds,Fc_out,Fc,FList=[Fc_in,CO2_in],Descr=descr,Units=units)
        else:
            log.error('CorrectFcForStorage: zms expected but not found in General section of control file')
    else:
        log.error('CorrectFcForStorage: section General expected but not found in control file')

def CorrectFg(cf,ds):
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='CFgArgs'):
        List = cf['FunctionArgs']['CFgArgs'].keys()
        for i in range(len(List)):
            CFgArgs = ast.literal_eval(cf['FunctionArgs']['CFgArgs'][str(i)])
            CorrectFgForStorage(cf,ds,Fg_out=CFgArgs[0],Fg_in=CFgArgs[1],Ts_in=CFgArgs[2],SWC_in=CFgArgs[3])
        return
    
    CorrectFgForStorage(cf,ds)

def CorrectFgForStorage(cf,ds,Fg_out='Fg',Fg_in='Fg',Ts_in='Ts',SWC_in='Sws'):
    """
        Correct ground heat flux for storage in the layer above the heat flux plate
        
        Usage qcts.CorrectFgForStorage(cf,ds,Fg_out,Fg_in,Ts_in,Sws_in)
        ds: data structure
        Fg_out: output soil heat flux variable to ds.  Example: 'Fg'
        Fg_in: input soil heat flux in ds.  Example: 'Fg_Av'
        Ts_in: input soil temperature in ds.  Example: 'Ts'
        
        Parameters loaded from control file:
            FgDepth: Depth of soil heat flux plates, m
            BulkDensity: soil bulk density, kg/m3
            OrganicContent: soil organic content, fraction
            SwsDefault: default value of soil moisture content used when no sensors present
        """
    log.info(' Correcting soil heat flux for storage')
    d = max(0.0,min(0.5,float(cf['Soil']['FgDepth'])))
    bd = max(1200.0,min(2500.0,float(cf['Soil']['BulkDensity'])))
    oc = max(0.0,min(1.0,float(cf['Soil']['OrganicContent'])))
    mc = 1.0 - oc
    Fg,f = qcutils.GetSeriesasMA(ds,Fg_in)        # raw soil heat flux
    nRecs = len(Fg)                               # number of records in series
    Ts,f = qcutils.GetSeriesasMA(ds,Ts_in)        # soil temperature
    #Sws,f = qcutils.GetSeriesasMA(ds,Sws_in)      # volumetric soil moisture
    Sws_default = min(1.0,max(0.0,float(cf['Soil']['SwsDefault'])))
    if len(SWC_in) == 0:
        slist = []
        if qcutils.cfkeycheck(cf,Base='Soil',ThisOne='SwsSeries'):
            slist = ast.literal_eval(cf['Soil']['SwsSeries'])
        if len(slist)==0:
            Sws = numpy.ones(nRecs)*Sws_default
        elif len(slist)==1:
            Sws,f = qcutils.GetSeriesasMA(ds,slist[0])
        else:
            MergeSeries(ds,'Sws',slist,[0,10])
            Sws,f = qcutils.GetSeriesasMA(ds,'Sws')
    else:
        slist = SWC_in
        Sws,f = qcutils.GetSeriesasMA(ds,SWC_in)
    log.info('  CorrectForStorage: Sws_in is '+str(slist))
    iom = numpy.where(numpy.mod(f,10)!=0)[0]
    if len(iom)!=0:
        Sws[iom] = Sws_default
    dTs = numpy.ma.zeros(nRecs)
    dTs[1:] = numpy.diff(Ts)
    dt = numpy.ma.zeros(nRecs)
    dt[1:] = numpy.diff(date2num(ds.series['DateTime']['Data']))*float(86400)
    dt[0] = dt[1]
    Cs = mc*bd*c.Cd + oc*bd*c.Co + Sws*c.rho_water*c.Cw
    S = Cs*(dTs/dt)*d
    Fg_o = Fg + S
    qcutils.CreateSeries(ds,Fg_out,Fg_o,FList=[Fg_in],Descr='Soil heat flux corrected for storage',Units='W/m2',Standard='downward_heat_flux_in_soil')
    qcutils.CreateSeries(ds,'S',S,FList=[Fg_in],Descr='Soil heat flux storage',Units='W/m2')
    qcutils.CreateSeries(ds,'Cs',Cs,FList=[Fg_in],Descr='Specific heat capacity',Units='J/m3/K')

def CorrectSWC(cf,ds):
    """
        Correct soil moisture data using calibration curve developed from
        collected soil samples.  To avoid unrealistic or unphysical extreme
        values upon extrapolation, exponential and logarithmic using ln
        functions are applied to small and large values, respectively.
        Threshold values where one model replaces the other is determined where
        the functions cross.  The logarithmic curve is constrained at with a
        point at which the soil measurement = field porosity and the sensor
        measurement is maximised under saturation at field capacity.
        
        Usage qcts.CorrectSWC(cf,ds)
        cf: control file
        ds: data structure
        
        Parameters loaded from control file:
            SWCempList: list of raw CS616 variables
            SWCoutList: list of corrected CS616 variables
            SWCattr:  list of meta-data attributes for corrected CS616 variables
            SWC_a0: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            SWC_a1: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            SWC_b0: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            SWC_b1: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            SWC_t: threshold parameter for switching from exponential to logarithmic model
            TDRempList: list of raw CS610 variables
            TDRoutList: list of corrected CS610 variables
            TDRattr:  list of meta-data attributes for corrected CS610 variables
            TDRlinList: list of deep TDR probes requiring post-hoc linear correction to match empirical samples
            TDR_a0: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            TDR_a1: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            TDR_b0: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            TDR_b1: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            TDR_t: threshold parameter for switching from exponential to logarithmic model
        """
    SWCempList = ast.literal_eval(cf['Soil']['empSWCin'])
    SWCoutList = ast.literal_eval(cf['Soil']['empSWCout'])
    SWCattr = ast.literal_eval(cf['Soil']['SWCattr'])
    if cf['Soil']['TDR']=='Yes':
        TDRempList = ast.literal_eval(cf['Soil']['empTDRin'])
        TDRoutList = ast.literal_eval(cf['Soil']['empTDRout'])
        TDRlinList = ast.literal_eval(cf['Soil']['linTDRin'])
        TDRattr = ast.literal_eval(cf['Soil']['TDRattr'])
        TDR_a0 = float(cf['Soil']['TDR_a0'])
        TDR_a1 = float(cf['Soil']['TDR_a1'])
        TDR_b0 = float(cf['Soil']['TDR_b0'])
        TDR_b1 = float(cf['Soil']['TDR_b1'])
        TDR_t = float(cf['Soil']['TDR_t'])
    SWC_a0 = float(cf['Soil']['SWC_a0'])
    SWC_a1 = float(cf['Soil']['SWC_a1'])
    SWC_b0 = float(cf['Soil']['SWC_b0'])
    SWC_b1 = float(cf['Soil']['SWC_b1'])
    SWC_t = float(cf['Soil']['SWC_t'])
    
    for i in range(len(SWCempList)):
        log.info('  Applying empirical correction to '+SWCempList[i])
        invar = SWCempList[i]
        outvar = SWCoutList[i]
        attr = SWCattr[i]
        Sws,f = qcutils.GetSeriesasMA(ds,invar)
        
        nRecs = len(Sws)
        
        Sws_out = numpy.ma.empty(nRecs,float)
        Sws_out.fill(-9999)
        Sws_out.mask = numpy.ma.empty(nRecs,bool)
        Sws_out.mask.fill(True)
        
        index_high = numpy.ma.where((Sws.mask == False) & (Sws > SWC_t))[0]
        index_low = numpy.ma.where((Sws.mask == False) & (Sws < SWC_t))[0]
        
        Sws_out[index_low] = SWC_b0 * numpy.exp(SWC_b1 * Sws[index_low])
        Sws_out[index_high] = (SWC_a1 * numpy.log(Sws[index_high])) + SWC_a0
        
        qcutils.CreateSeries(ds,outvar,Sws_out,FList=[invar],Descr=attr,Units='cm3 water/cm3 soil',Standard='soil_moisture_content')
    if cf['Soil']['TDR']=='Yes':
        for i in range(len(TDRempList)):
            log.info('  Applying empirical correction to '+TDRempList[i])
            invar = TDRempList[i]
            outvar = TDRoutList[i]
            attr = TDRattr[i]
            Sws,f = qcutils.GetSeriesasMA(ds,invar)
            
            nRecs = len(Sws)
            
            Sws_out = numpy.ma.empty(nRecs,float)
            Sws_out.fill(-9999)
            Sws_out.mask = numpy.ma.empty(nRecs,bool)
            Sws_out.mask.fill(True)
            
            index_high = numpy.ma.where((Sws.mask == False) & (Sws > TDR_t))[0]
            index_low = numpy.ma.where((Sws.mask == False) & (Sws < TDR_t))[0]
            
            Sws_out[index_low] = TDR_b0 * numpy.exp(TDR_b1 * Sws[index_low])
            Sws_out[index_high] = (TDR_a1 * numpy.log(Sws[index_high])) + TDR_a0
            
            qcutils.CreateSeries(ds,outvar,Sws_out,FList=[invar],Descr=attr,Units='cm3 water/cm3 soil',Standard='soil_moisture_content')

def CorrectWindDirection(cf,ds,Wd_in):
    """
        Correct wind direction for mis-aligned sensor direction.
        
        Usage qcts.CorrectWindDirection(cf,ds,Wd_in)
        cf: control file
        ds: data structure
        Wd_in: input/output wind direction variable in ds.  Example: 'Wd_CSAT'
        """
    log.info(' Correcting wind direction')
    Wd,f = qcutils.GetSeriesasMA(ds,Wd_in)
    ldt = ds.series['DateTime']['Data']
    KeyList = cf['Variables'][Wd_in]['Correction'].keys()
    for i in range(len(KeyList)):
        ItemList = ast.literal_eval(cf['Variables'][Wd_in]['Correction'][str(i)])
        try:
            si = ldt.index(datetime.datetime.strptime(ItemList[0],'%Y-%m-%d %H:%M'))
        except ValueError:
            si = 0
        try:
            ei = ldt.index(datetime.datetime.strptime(ItemList[1],'%Y-%m-%d %H:%M')) + 1
        except ValueError:
            ei = -1
        Correction = float(ItemList[2])
        Wd[si:ei] = Wd[si:ei] + Correction
    Wd = numpy.mod(Wd,float(360))
    ds.series[Wd_in]['Data'] = numpy.ma.filled(Wd,float(-9999))

def do_attributes(cf,ds):
    """
        Import attriubes in xl2nc control file to netCDF dataset.  Included
        global and variable attributes.  Also attach flag definitions to global
        meta-data for reference.
        
        Usage qcts.do_attributes(cf,ds)
        cf: control file
        ds: data structure
        """
    log.info(' Getting the attributes given in control file')
    if 'Global' in cf.keys():
        for gattr in cf['Global'].keys():
            ds.globalattributes[gattr] = cf['Global'][gattr]
        ds.globalattributes['Flag0'] = 'Good data'
        ds.globalattributes['Flag1'] = 'QA/QC: -9999 in level 1 dataset'
        ds.globalattributes['Flag2'] = 'QA/QC: L2 Range Check'
        ds.globalattributes['Flag3'] = 'QA/QC: CSAT Diagnostic'
        ds.globalattributes['Flag4'] = 'QA/QC: LI7500 Diagnostic'
        ds.globalattributes['Flag5'] = 'QA/QC: L2 Diurnal SD Check'
        ds.globalattributes['Flag6'] = 'QA/QC: Excluded Dates'
        ds.globalattributes['Flag7'] = 'QA/QC: Excluded Hours'
        ds.globalattributes['Flag8'] = 'albedo: bad Fsd < threshold (290 W/m2 default) only if bad time flag not set'
        ds.globalattributes['Flag9'] = 'albedo: bad time flag (not midday 10.00 to 14.00)'
        ds.globalattributes['Flag10'] = 'Corrections: Apply Linear'
        ds.globalattributes['Flag11'] = 'Corrections/Combinations: Coordinate Rotation (Ux, Uy, Uz, UxT, UyT, UzT, UxA, UyA, UzA, UxC, UyC, UzC, UxUz, UxUx, UxUy, UyUz, UxUy, UyUy)'
        ds.globalattributes['Flag12'] = 'Corrections/Combinations: Massman Frequency Attenuation Correction (Coord Rotation, Tv_CSAT, Ah_HMP, ps)'
        ds.globalattributes['Flag13'] = 'Corrections/Combinations: Virtual to Actual Fh (Coord Rotation, Massman, Ta_HMP)'
        ds.globalattributes['Flag14'] = 'Corrections/Combinations: WPL correction for flux effects on density measurements (Coord Rotation, Massman, Fhv to Fh, Cc_7500_Av)'
        ds.globalattributes['Flag15'] = 'Corrections/Combinations: Ta from Tv'
        ds.globalattributes['Flag16'] = 'Corrections/Combinations: L3 Range Check'
        ds.globalattributes['Flag17'] = 'Corrections/Combinations: L3 Diurnal SD Check'
        ds.globalattributes['Flag18'] = 'Corrections/Combinations: u* filter'
        ds.globalattributes['Flag19'] = 'Corrections/Combinations: Gap coordination'
        ds.globalattributes['Flag30'] = 'GapFilling: Flux Gap Filled by ANN (SOLO)'
        ds.globalattributes['Flag31'] = 'GapFilling: Flux Gap not Filled by ANN'
        ds.globalattributes['Flag40'] = 'GapFilling: Met Gap Filled from Climatology'
        ds.globalattributes['Flag50'] = 'GapFilling: Gap Filled from Ratios'
        ds.globalattributes['Flag60'] = 'GapFilling: Gap Filled by Interpolation'
        ds.globalattributes['Flag70'] = 'GapFilling: Gap Filled by Replacement'
        ds.globalattributes['Flag80'] = 'GapFilling: u* from Fh'
        ds.globalattributes['Flag81'] = 'GapFilling: u* not from Fh'
        ds.globalattributes['Flag82'] = 'GapFilling: L4 Range Check'
        ds.globalattributes['Flag83'] = 'GapFilling: L4 Diurnal SD Check'
        ds.globalattributes['Flag90'] = 'Partitioning Night: Re computed from exponential temperature response curves'
        ds.globalattributes['Flag100'] = 'Partitioning Day: GPP/Re computed from light-response curves, GPP = Re - Fc'
        ds.globalattributes['Flag110'] = 'Partitioning Day: GPP night mask'
        ds.globalattributes['Flag120'] = 'Partitioning Day: Fc > Re, GPP = 0, Re = Fc'
        ds.globalattributes['Flag121'] = 'Footprint: Date filter'
        ds.globalattributes['Flag122'] = 'Footprint: no solution'
        ds.globalattributes['Flag131'] = 'Penman-Monteith: bad rav or rC only if bad Uavg, bad Fe and bad Fsd flags not set'
        ds.globalattributes['Flag132'] = 'Penman-Monteith: bad Fe < threshold (0 W/m2 default) only if bad Fsd flag not set'
        ds.globalattributes['Flag133'] = 'Penman-Monteith: bad Fsd < threshold (10 W/m2 default)'
        ds.globalattributes['Flag134'] = 'Penman-Monteith: Uavg == 0 (undefined aerodynamic resistance under calm conditions) only if bad Fe and bad Fsd flags not set'
        ds.globalattributes['Flag140'] = 'Penman-Monteith 2-layer: rav_base short-circuit'
        ds.globalattributes['Flag150'] = 'Penman-Monteith 2-layer: rav_top short-circuit'
        ds.globalattributes['Flag151'] = 'Penman-Monteith 2-layer: rav_top not short-circuit (rav_base undefined)'
        ds.globalattributes['Flag160'] = 'Penman-Monteith 2-layer: parallel circuit'
        ds.globalattributes['Flag161'] = 'Penman-Monteith 2-layer: not parallel circuit (rav_full short-circuit)'
    for ThisOne in ds.series.keys():
        if ThisOne in cf['Variables']:
            if 'Attr' in cf['Variables'][ThisOne].keys():
                ds.series[ThisOne]['Attr'] = {}
                for attr in cf['Variables'][ThisOne]['Attr'].keys():
                    ds.series[ThisOne]['Attr'][attr] = cf['Variables'][ThisOne]['Attr'][attr]

def do_bulkRichardson(cf,ds):
    IncludeList = cf['Rb']['series'].keys()
    NumHeights = len(IncludeList)
    # calculate layer values
    for i in range(NumHeights-1):
        IncludeHeightList = ast.literal_eval(cf['Rb']['series'][str(i)])
        NextHeightList = ast.literal_eval(cf['Rb']['series'][str(i+1)])
        U_top,f = qcutils.GetSeriesasMA(ds,NextHeightList[1])
        U_bottom,f = qcutils.GetSeriesasMA(ds,IncludeHeightList[1])
        Tvp_top,f = qcutils.GetSeriesasMA(ds,NextHeightList[2])
        Tvp_bottom,f = qcutils.GetSeriesasMA(ds,IncludeHeightList[2])
        delta_z = float(NextHeightList[0]) - float(IncludeHeightList[0])
        delta_Tvp = Tvp_top - Tvp_bottom
        delta_U = U_top - U_bottom
        srclist = qcutils.GetAverageList(cf,IncludeHeightList[3])
        if len(srclist) > 0:
            AverageSeriesByElements(ds,IncludeHeightList[3],srclist)
        
        Tvp_bar,f = qcutils.GetSeriesasMA(ds,IncludeHeightList[3])
        Rb = (9.8 * delta_Tvp * delta_z) / (Tvp_bar * (delta_U ** 2))
        qcutils.CreateSeries(ds,IncludeHeightList[4],delta_U,FList=[IncludeHeightList[1],IncludeHeightList[2],IncludeHeightList[3],'Fc'],Descr='U_upper less U_lower',Units='m/s')
        qcutils.CreateSeries(ds,IncludeHeightList[5],delta_Tvp,FList=[IncludeHeightList[1],IncludeHeightList[2],IncludeHeightList[3],'Fc'],Descr='Tvp_upper less Tvp_lower',Units='m/s')
        qcutils.CreateSeries(ds,IncludeHeightList[6],Rb,FList=[IncludeHeightList[1],IncludeHeightList[2],IncludeHeightList[3],'Fc'],Descr='Bulk Richardson number',Units='none')
        flaglist = [IncludeHeightList[4],IncludeHeightList[5],IncludeHeightList[6]]
        for ThisOne in flaglist:
            flag = numpy.where(numpy.mod(ds.series[ThisOne]['Flag'],10)!=0)[0]
            ds.series[ThisOne]['Data'][flag] = -9999

def do_climatology(cf,ds):
    if qcutils.cfkeycheck(cf,Base='Climatology',ThisOne='met'):
        MList = ast.literal_eval(cf['Climatology']['met'])
    else:
        MList = ['Ta','Ah','Cc_7500_Av','Ws_CSAT','Wd_CSAT','ps']
    
    if qcutils.cfkeycheck(cf,Base='Climatology',ThisOne='rad'):
        RList = ast.literal_eval(cf['Climatology']['rad'])
    else:
        RList = ['Fld','Flu','Fn','Fsd','Fsu']
    
    if qcutils.cfkeycheck(cf,Base='Climatology',ThisOne='soil'):
        SList = ast.literal_eval(cf['Climatology']['soil'])
    else:
        SList = ['Ts','Sws','Fg']
    
    if qcutils.cfkeycheck(cf,Base='Climatology',ThisOne='flux'):
        FList = ast.literal_eval(cf['Climatology']['flux'])
    else:
        FList = ['Fc','Fe','Fh','Fm','ustar']
    
    OList = MList+RList+SList+FList                                   # output series
    qcts.ComputeClimatology(cf,ds,OList)

def do_footprint_2d(cf,ds,level='L3'):
    log.info(' Calculating 2D footprint')
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='zm'):
        zm = float(cf['Footprint']['zm'])
    
    if zm<1.0:
        log.error('zm needs to be larger than 1 m')
        return
    
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='zc'):
        zc = float(cf['Footprint']['zc'])
    
    d = 2 / 3 * zc
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='z0'):
        znot = float(cf['Footprint']['z0'])
    
    if znot<0.0:
        log.error('z0 needs to be larger than 0 m')
        return
    
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='r'):
        r = int(cf['Footprint']['r'])
    
    if r>96.0:
        log.error('r needs to be smaller than 96')
        return
    
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ExcludeHours') and cf['Footprint']['ExcludeHours'] == 'True':
        qcck.do_excludehours(cf,ds,'L')
    
    sigmaw,f = qcutils.GetSeriesasMA(ds,'ww')
    sigmav,f = qcutils.GetSeriesasMA(ds,'vv')
    ustar,f = qcutils.GetSeriesasMA(ds,'ustar')
    L,Lf = qcutils.GetSeriesasMA(ds,'L')
    Fsd,f = qcutils.GetSeriesasMA(ds,'Fsd')
    n = len(L)
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='AnalysisDates'):
        ldt = ds.series['DateTime']['Data']
        IncludeList = cf['Footprint']['AnalysisDates'].keys()
        NumDates = len(IncludeList)
        analysisflag = numpy.zeros(n,int)
        for i in range(NumDates):
            IncludeDateList = ast.literal_eval(cf['Footprint']['AnalysisDates'][str(i)])
            try:
                si = ldt.index(datetime.datetime.strptime(IncludeDateList[0],'%Y-%m-%d %H:%M'))
            except ValueError:
                si = -1
            
            try:
                ei = ldt.index(datetime.datetime.strptime(IncludeDateList[1],'%Y-%m-%d %H:%M')) + 1
            except ValueError:
                ei = -1
            
            analysisflag[si:ei] = 1
        
        index = numpy.where(analysisflag == 0)[0]
        Lf[index] = 9999
    
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ExcludeDay') and cf['Footprint']['ExcludeDay'] == 'True':
        Dayindex = numpy.where(Fsd > 10)[0]
        Lf[Dayindex] = 7
    
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ExcludeNight') and cf['Footprint']['ExcludeNight'] == 'True':
        Nightindex = numpy.where(Fsd < 10)[0]
        Lf[Nightindex] = 7
    
    zeta = numpy.ma.zeros(n,dtype=float)
    Lfindex = numpy.where(numpy.mod(Lf,10)!=0)[0]
    zetaindex = numpy.where(numpy.mod(Lf,10)==0)[0]
    if len(zetaindex) == 0:
        log.warn('   Footprint:  no observations passed filtering')
        return
    
    zeta[Lfindex] = 9999999
    zeta[zetaindex] = (zm - d) / L[zetaindex]
    
    index_zero_L = numpy.ma.where(zeta > 9999998)[0]
    index_neutral = numpy.ma.where((zeta > -0.1) & (zeta < 0.1))[0]
    index_slight_stable = numpy.ma.where((zeta > 0.1) & (zeta < 1))[0]
    index_stable = numpy.ma.where((zeta > 1) & (zeta < 2))[0]
    index_very_stable = numpy.ma.where((zeta > 2) & (zeta < 9999999))[0]
    index_slight_unstable = numpy.ma.where((zeta < -0.1) & (zeta > -1))[0]
    index_unstable = numpy.ma.where((zeta < -1) & (zeta > -2))[0]
    index_very_unstable = numpy.ma.where(zeta < -2)[0]
    h = numpy.ma.zeros(n,dtype=float)
    log.info('  '+str(len(index_zero_L))+':  masked L (incl gaps and not dates)')
    log.info('  '+str(len(index_neutral))+':  neutral, -0.1 < zeta < 0.1')
    log.info('  '+str(len(index_slight_stable))+':  slightly stable, 0.1 < zeta < 1')
    log.info('  '+str(len(index_stable))+':  stable, 1 < zeta < 2')
    log.info('  '+str(len(index_very_stable))+':  very stable, zeta > 2')
    log.info('  '+str(len(index_slight_unstable))+':  slightly unstable, -0.1 > zeta > -1')
    log.info('  '+str(len(index_unstable))+':  unstable, -1 > zeta > -2')
    log.info('  '+str(len(index_very_unstable))+':  very unstable, zeta < -2')
    h[index_zero_L] = numpy.float(0)
    h[index_very_unstable] = numpy.float(2000)
    h[index_unstable] = numpy.float(1500)
    h[index_slight_unstable] = numpy.float(1200)
    h[index_neutral] = numpy.float(1000)
    h[index_slight_stable] = numpy.float(800)
    h[index_stable] = numpy.float(250)
    h[index_very_stable] = numpy.float(200)
    
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='wd'):
        wdin = cf['Footprint']['wd']
    else:
        wdin = 'Wd_CSAT'
    
    if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='Fluxes'):
        Fluxesin = ast.literal_eval(cf['Footprint']['Fluxes'])
        Fc,fFc = qcutils.GetSeriesasMA(ds,Fluxesin[0])
        Fe,fFe = qcutils.GetSeriesasMA(ds,Fluxesin[1])
    else:
        if level == 'L3':
            Fc,fFc = qcutils.GetSeriesasMA(ds,'Fc')
            Fe,fFe = qcutils.GetSeriesasMA(ds,'Fe')
        elif level == 'L4':
            Fc,fFc = qcutils.GetSeriesasMA(ds,'GPP')
            Fe,fFe = qcutils.GetSeriesasMA(ds,'Re')
        else:
            log.error('  Footprint:  invalid input fluxes or analysis level')
            return
    
    wd,f = qcutils.GetSeriesasMA(ds,wdin)
    eta,f = qcutils.GetSeriesasMA(ds,'eta')
    xr = numpy.ma.zeros(n,dtype=float)
    if qcutils.cfkeycheck(cf,Base='Output',ThisOne='FootprintFileDataType') and cf['Output']['FootprintFileDataType'] == 'Climatology':
        if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ClimateXmin') and qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ClimateXmax') and qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ClimateYmin') and qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ClimateYmax') and qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='ClimatePixel'):
            n = ((float(cf['Footprint']['ClimateXmax'])) - (float(cf['Footprint']['ClimateXmin']))) / (float(cf['Footprint']['ClimatePixel']))
            m = ((float(cf['Footprint']['ClimateYmax'])) - (float(cf['Footprint']['ClimateYmin']))) / (float(cf['Footprint']['ClimatePixel']))
            xmin = (float(cf['Footprint']['ClimateXmin']))
            xmax = (float(cf['Footprint']['ClimateXmax']))
            ymin = (float(cf['Footprint']['ClimateYmin']))
            ymax = (float(cf['Footprint']['ClimateYmax']))
            p = (float(cf['Footprint']['ClimatePixel']))
            fc_c_2d = numpy.ma.zeros((n,m),dtype=float)
            fc_e_2d = numpy.ma.zeros((n,m),dtype=float)
        else:
            log.error('  Footprint climatology: Spatial parameters missing from controlfile')
            return
    
    do_index = numpy.where((sigmaw > 0) & (sigmav > 0) & (ustar > 0.2) & (h > 1) & (h > zm))[0]
    for i in range(len(do_index)):
        if qcutils.cfkeycheck(cf,Base='Footprint',ThisOne='loglist') and cf['Footprint']['loglist'] == 'True':
            log.info('    Footprint: '+str(ds.series['DateTime']['Data'][do_index[i]]))
        
        if numpy.mod(fFc[do_index[i]],10)!=0 or numpy.mod(fFe[do_index[i]],10)!=0:
            Fc[do_index[i]] = numpy.float(-9999)
            Fe[do_index[i]] = numpy.float(-9999)
        
        if qcutils.cfkeycheck(cf,Base='Output',ThisOne='FootprintFileDataType') and cf['Output']['FootprintFileDataType'] == 'Climatology' and qcutils.cfkeycheck(cf,Base='Output',ThisOne='FootprintFile') and cf['Output']['FootprintFile'] == 'True':
            xr[do_index[i]],x_2d,y_2d,fw_c_2d,fw_e_2d,filenames,labels = footprint_2d(cf,sigmaw[do_index[i]],sigmav[do_index[i]],ustar[do_index[i]],zm,h[do_index[i]],znot,r,wd[do_index[i]],zeta[do_index[i]],L[do_index[i]],zc,ds.series['DateTime']['Data'][do_index[i]],eta[do_index[i]],Fc[do_index[i]],Fe[do_index[i]],level)
            fc_c_2d,fc_e_2d,fc_x2d,fc_y2d = footprint_climatology(fc_c_2d,fc_e_2d,x_2d,y_2d,fw_c_2d,fw_e_2d,n,m,xmin,xmax,ymin,ymax,p)
        else:
            xr[do_index[i]] = footprint_2d(cf,sigmaw[do_index[i]],sigmav[do_index[i]],ustar[do_index[i]],zm,h[do_index[i]],znot,r,wd[do_index[i]],zeta[do_index[i]],L[do_index[i]],zc,ds.series['DateTime']['Data'][do_index[i]],eta[do_index[i]],Fc[do_index[i]],Fe[do_index[i]],level)
        
    if qcutils.cfkeycheck(cf,Base='Output',ThisOne='FootprintFileDataType') and cf['Output']['FootprintFileDataType'] == 'Climatology' and qcutils.cfkeycheck(cf,Base='Output',ThisOne='FootprintFile') and cf['Output']['FootprintFile'] == 'True':
        if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileType') and cf['Output']['FootprintFileType'] == 'Vector':
            footprint_vector_out(filenames[0],fc_x2d,fc_y2d,fc_c_2d,labels[0])
            footprint_vector_out(filenames[2],fc_x2d,fc_y2d,fc_e_2d,labels[1])
        elif qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileType') and cf['Output']['FootprintFileType'] == 'Matrix':
            footprint_matrix_out(filenames[1],fc_x2d,fc_y2d,fc_c_2d)
            footprint_matrix_out(filenames[3],fc_x2d,fc_y2d,fc_e_2d)
        else:
            log.error('  Footprint climatology:  FootprintFileType (Vector or Matrix) not defined in controlfile')
        
    qcutils.CreateSeries(ds,'xr',xr,FList=['L','ww','vv','ustar'],Descr='integrated footprint in the direction of the wind',Units='m')
    flag_index = numpy.ma.where((xr == 0) & (numpy.mod(ds.series['xr']['Flag'],10)==0))[0]
    ustar_index = numpy.ma.where(ustar < 0.2)[0]
    date_index = numpy.ma.where(Lf == 9999)[0]
    ds.series['xr']['Flag'][flag_index] = 122
    ds.series['xr']['Flag'][ustar_index] = 18
    ds.series['xr']['Flag'][date_index] = 121
    index = numpy.where((numpy.mod(ds.series['xr']['Flag'],10)!=0))[0]    # find the elements with flag != 0, 10, 20 etc
    ds.series['xr']['Data'][index] = -9999

def do_functions(cf,ds):
    log.info(' Resolving functions given in control file')
    for ThisOne in cf['Variables'].keys():
        if 'Function' in cf['Variables'][ThisOne].keys():
            ds.series[ThisOne] = {}
            FunctionList = cf['Variables'][ThisOne]['Function'].keys()
            if len(FunctionList) == 1:
                i = 0
                if 'Square' in cf['Variables'][ThisOne]['Function'][str(i)].keys() and 'Parent' in cf['Variables'][ThisOne]['Function'][str(i)]['Square'].keys():
                    Parent = cf['Variables'][ThisOne]['Function'][str(i)]['Square']['Parent']
                    ds.series[ThisOne]['Data'] = qcts.Square(ds.series[Parent]['Data'])
                    nRecs = numpy.size(ds.series[ThisOne]['Data'])
                    if 'Flag' not in ds.series[ThisOne].keys():
                        ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                        if 'Flag' in ds.series[Parent]:
                            ds.series[ThisOne]['Flag'] = ds.series[Parent]['Flag']
                        else:
                            ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                elif 'SquareRoot' in cf['Variables'][ThisOne]['Function'][str(i)].keys() and 'Parent' in cf['Variables'][ThisOne]['Function'][str(i)]['SquareRoot'].keys():
                    Parent = cf['Variables'][ThisOne]['Function'][str(i)]['SquareRoot']['Parent']
                    ds.series[ThisOne]['Data'] = qcts.SquareRoot(ds.series[Parent]['Data'])
                    nRecs = numpy.size(ds.series[ThisOne]['Data'])
                    if 'Flag' not in ds.series[ThisOne].keys():
                        ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                        if 'Flag' in ds.series[Parent]:
                            ds.series[ThisOne]['Flag'] = ds.series[Parent]['Flag']
                        else:
                            ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                else:
                    log.error ('Function missing or unknown for variable'+ThisOne)
                    return
            else:
                for i in range(len(FunctionList)):
                    if 'Square' in cf['Variables'][ThisOne]['Function'][str(i)].keys() and 'Parent' in cf['Variables'][ThisOne]['Function'][str(i)]['Square'].keys():
                        Parent = cf['Variables'][ThisOne]['Function'][str(i)]['Square']['Parent']
                        ds.series[ThisOne]['Data'] = qcts.Square(ds.series[Parent]['Data'])
                        nRecs = numpy.size(ds.series[ThisOne]['Data'])
                        if 'Flag' not in ds.series[ThisOne].keys():
                            ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                            if 'Flag' in ds.series[Parent]:
                                ds.series[ThisOne]['Flag'] = ds.series[Parent]['Flag']
                            else:
                                ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                    elif 'SquareRoot' in cf['Variables'][ThisOne]['Function'][str(i)].keys() and 'Parent' in cf['Variables'][ThisOne]['Function'][str(i)]['SquareRoot'].keys():
                        Parent = cf['Variables'][ThisOne]['Function'][str(i)]['SquareRoot']['Parent']
                        ds.series[ThisOne]['Data'] = qcts.SquareRoot(ds.series[Parent]['Data'])
                        nRecs = numpy.size(ds.series[ThisOne]['Data'])
                        if 'Flag' not in ds.series[ThisOne].keys():
                            ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                            if 'Flag' in ds.series[Parent]:
                                ds.series[ThisOne]['Flag'] = ds.series[Parent]['Flag']
                            else:
                                ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,int)
                    else:
                        log.error ('Function missing or unknown for variable'+ThisOne)
                        return

def do_PenmanMonteith(cf,ds):
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cdmethod'):
        Cdmethod = cf['PenmanMonteith']['Cdmethod']
    else:
        Cdmethod = 'False'
    
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Cemethod'):
        Cemethod = cf['PenmanMonteith']['Cemethod']
    else:
        Cemethod = 'False'
    
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='Ce_2layer'):
        Ce_2layer = cf['PenmanMonteith']['Ce_2layer']
    else:
        Ce_2layer = 'False'
    
    if Cdmethod != 'True' and Cemethod != 'True' and Ce_2layer != 'True':
        log.error(' PenmanMontieth:  no method selected')
        return
        
    prep_aerodynamicresistance(cf,ds,Cdmethod,Cemethod,Ce_2layer)
    return

def do_solo(cf,ds4,Fc_in='Fc',Fe_in='Fe',Fh_in='Fh',Fc_out='Fc',Fe_out='Fe',Fh_out='Fh'):
    ''' duplicate gapfilled fluxes for graphing comparison'''
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='SOLOvars'):
        invars = ast.literal_eval(cf['FunctionArgs']['SOLOvars'])
        Fc_in = invars[0]
        Fe_in = invars[1]
        Fh_in = invars[2]
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='SOLOplot'):
        outvars = ast.literal_eval(cf['FunctionArgs']['SOLOplot'])
        Fc_out = outvars[0]
        Fe_out = outvars[1]
        Fh_out = outvars[2]
    # add relevant meteorological values to L3 data
    log.info(' Adding standard met variables to database')
    CalculateMeteorologicalVariables(cf,ds4)
    ds4.globalattributes['L4Functions'] = ds4.globalattributes['L4Functions']+', CalculateMetVars'
    if Fe_in in ds4.series.keys():
        Fe,flag = qcutils.GetSeriesasMA(ds4,Fe_in)
        qcutils.CreateSeries(ds4,Fe_out,Fe,Flag=flag,Descr='ANN gapfilled Latent Heat Flux',Units='W/m2',Standard='surface_upward_latent_heat_flux')
    if Fc_in in ds4.series.keys():
        Fc,flag = qcutils.GetSeriesasMA(ds4,Fc_in)
        qcutils.CreateSeries(ds4,Fc_out,Fc,Flag=flag,Descr='ANN gapfilled Carbon Flux',Units='mg/m2/s')
    if Fh_in in ds4.series.keys():
        Fh,flag = qcutils.GetSeriesasMA(ds4,Fh_in)
        qcutils.CreateSeries(ds4,Fh_out,Fh,Flag=flag,Descr='ANN gapfilled Sensible Heat Flux',Units='W/m2',Standard='surface_upward_sensible_heat_flux')

def do_sums(cf,ds):
    # compute daily statistics
    if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='SumList'):
        SumList = ast.literal_eval(cf['Sums']['SumList'])
    else:
        SumList = ['Rain','ET','Energy','Radiation','Carbon']
    
    if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='SubSumList'):
        SubSumList = ast.literal_eval(cf['Sums']['SubSumList'])
    else:
        SubSumList = []
    
    if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='MinMaxList'):
        MinMaxList = ast.literal_eval(cf['Sums']['MinMaxList'])
    else:
        MinMaxList = ['Ta_EC','Vbat','Tpanel','Carbon']
    
    if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='MeanList'):
        MeanList = ast.literal_eval(cf['Sums']['MeanList'])
    else:
        MeanList = ['Ta_EC','Tpanel']
    
    if qcutils.cfkeycheck(cf,Base='Sums',ThisOne='SoilList'):
        SoilList = ast.literal_eval(cf['Sums']['SoilList'])
    else:
        SoilList = []
    
    StatsList = SumList + MinMaxList + MeanList + SoilList
    if len(StatsList) > 0:
        qcts.ComputeDailySums(cf,ds,SumList,SubSumList,MinMaxList,MeanList,SoilList)

def do_WPL(cf,ds,cov=''):
    if cov == 'True':
        Fe_WPLcov(cf,ds)
        Fc_WPLcov(cf,ds)
        return
    
    Fe_WPL(cf,ds)
    Fc_WPL(cf,ds)

def extrapolate_humidity(zq_ref,zq_high,zq_low,q_high,q_low,fqh,fql):
    rise = zq_high - zq_low
    run = q_high - q_low
    qref = numpy.zeros(len(run)) + numpy.float(-9999)
    slope = numpy.zeros(len(run)) + numpy.float(-9999)
    index = numpy.where((numpy.mod(fqh,10)==0) & (numpy.mod(fql,10)==0))[0]
    slope[index] = rise / run[index]
    qref[index] = q_high[index] - ((zq_high - zq_ref) / slope[index])
    return qref

def Fc_WPL(cf,ds,Fc_wpl_out='Fc',Fc_raw_in='Fc',Fh_in='Fh',Fe_wpl_in='Fe',Ta_in='Ta',Ah_in='Ah',Cc_in='Cc_7500_Av',ps_in='ps'):
    """
        Apply Webb, Pearman and Leuning correction to carbon flux.  This
        correction is necessary to account for flux effects on density
        measurements.  Original formulation: Campbell Scientific
        
        Usage qcts.Fc_WPL(ds,Fc_wpl_out,Fc_raw_in,Fh_in,Fe_wpl_in,Ta_in,Ah_in,Cc_in,ps_in)
        ds: data structure
        Fc_wpl_out: output corrected carbon flux variable to ds.  Example: 'Fc_wpl'
        Fc_raw_in: input carbon flux in ds.  Example: 'Fc_raw'
        Fh_in: input sensible heat flux in ds.  Example: 'Fh_rv'
        Fe_wpl_in: input corrected latent heat flux in ds.  Example: 'Fe_wpl'
        Ta_in: input air temperature in ds.  Example: 'Ta_EC'
        Ah_in: input absolute humidity in ds.  Example: 'Ah_EC'
        Cc_in: input co2 density in ds.  Example: 'Cc_7500_Av'
        ps_in: input atmospheric pressure in ds.  Example: 'ps'
        
        Used for fluxes that are raw or rotated.
        
        Pre-requisite: CalculateFluxes, CalculateFluxes_Unrotated or CalculateFluxesRM
        Pre-requisite: FhvtoFh
        Pre-requisite: Fe_WPL
        
        Accepts meteorological constants or variables
        """
    log.info(' Applying WPL correction to Fc')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='CWPL'):
        Cargs = ast.literal_eval(cf['FunctionArgs']['CWPL'])
        Fc_wpl_out = Cargs[0]
        Fc_raw_in = Cargs[1]
        Fh_in = Cargs[2]
        Fe_wpl_in = Cargs[3]
        Ta_in = Cargs[4]
        Ah_in = Cargs[5]
        Cc_in = Cargs[6]
        ps_in = Cargs[7]
    Fc_raw,f = qcutils.GetSeriesasMA(ds,Fc_raw_in)
    Fh,f = qcutils.GetSeriesasMA(ds,Fh_in)
    Fe_wpl,f = qcutils.GetSeriesasMA(ds,Fe_wpl_in)
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_in)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_in)
    Cc,f = qcutils.GetSeriesasMA(ds,Cc_in)
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    rhod,f = qcutils.GetSeriesasMA(ds,'rhod')
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    nRecs = numpy.size(Fh)
    Fc_wpl_flag = numpy.zeros(nRecs,int)
    Ah = Ah/float(1000)                       # Absolute humidity from g/m3 to kg/m3
    sigma_wpl = Ah/rhod
    co2_wpl_Fe = 1.61*(Cc/rhod)*(Fe_wpl/Lv)
    co2_wpl_Fh = (1+(1.61*sigma_wpl))*Cc/(Ta+273.15)*Fh/(rhom*Cpm)
    Fc_wpl_data = Fc_raw+co2_wpl_Fe+co2_wpl_Fh
    qcutils.CreateSeries(ds,Fc_wpl_out,Fc_wpl_data,FList=[Fc_raw_in,Fh_in,Fe_wpl_in,Ta_in,Ah_in,Cc_in,ps_in],Descr='WPL corrected Fc',Units='mg/m2/s')
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='WPLFlag') and cf['General']['WPLFlag'] == 'True':
        testseries,f = qcutils.GetSeriesasMA(ds,Fc_wpl_out)
        mask = numpy.ma.getmask(testseries)
        index = numpy.where(mask.astype(int)==1)
        ds.series[Fc_wpl_out]['Flag'][index] = 14
    else:
        testseries,f = qcutils.GetSeriesasMA(ds,Fc_wpl_out)
        mask = numpy.ma.getmask(testseries)
        index = numpy.where((numpy.mod(f,10)==0) & (mask.astype(int)==1))    # find the elements with flag = 0, 10, 20 etc and masked (check for masked data with good data flag)
        ds.series[Fc_wpl_out]['Flag'][index] = 14

def Fc_WPLcov(cf,ds,Fc_wpl_out='Fc',wC_in='wC',Fh_in='Fh',wA_in='wA',Ta_in='Ta',Ah_in='Ah',Cc_in='Cc_7500_Av',ps_in='ps'):
    """
        Apply Webb, Pearman and Leuning correction to carbon flux using the
        original formulation (WPL80).  This correction is necessary to account
        for flux effects on density measurements.  This method uses the
        originally-published formulation using covariances rather than fluxes.
        The difference in the corrected fluxes using the two routines is minor
        and related to scaling the met variables.
        
        Usage qcts.Fc_WPLcov(ds,Fc_wpl_out,wC,Fh,wA,Ta,Ah,Cc,ps)
        ds: data structure
        Fc_wpl_out: output corrected carbon flux to ds.  Example: 'Fc_wpl'
        wC: input covariance(wC) in ds.  Example: 'wCM'
        Fh: input sensible heat flux in ds.  Example: 'Fh_rmv'
        wA: input covariance(wA) in ds.  Example: 'wAwpl'
        Ta: input air temperature in ds.  Example: 'Ta_HMP'
        Ah: input absolute humidity in ds.  Example: 'Ah_HMP'
        Cc: input co2 density in ds.  Example: 'Cc_7500_Av'
        ps: input atmospheric pressure in ds.  Example: 'ps'
        
        Pre-requisite: FhvtoFh
        Pre-requisite: Fe_WPLcov
        
        Accepts meteorological constants or variables
        """
    log.info(' Applying WPL correction to Fc')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='CWPL'):
        Cargs = ast.literal_eval(cf['FunctionArgs']['CWPL'])
        Fc_wpl_out = Cargs[0]
        wC_in = Cargs[1]
        Fh_in = Cargs[2]
        wA_in = Cargs[3]
        Ta_in = Cargs[4]
        Ah_in = Cargs[5]
        Cc_in = Cargs[6]
        ps_in = Cargs[7]
    wC,f = qcutils.GetSeriesasMA(ds,wC_in)
    Fh,f = qcutils.GetSeriesasMA(ds,Fh_in)
    wA,f = qcutils.GetSeriesasMA(ds,wA_in)
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_in)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_in)
    Cc,f = qcutils.GetSeriesasMA(ds,Cc_in)
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    Cpm,f = qcutils.GetSeriesasMA(ds,'Cpm')
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
    rhod,f = qcutils.GetSeriesasMA(ds,'rhod')
    nRecs = numpy.size(wC)
    TaK = Ta + 273.15
    Ah = Ah/float(1000)                       # Absolute humidity from g/m3 to kg/m3
    Cckg = Cc/float(1000000)                  # CO2 from mg/m3 to kg/m3
    sigma_wpl = Ah/rhod
    wT = Fh / (rhom * Cpm)
    Fc_wpl_data = wC + (1.61 * (Cckg / rhod) * wA) + ((1 + (1.61 * sigma_wpl)) * (Cc / TaK) * wT)
    qcutils.CreateSeries(ds,Fc_wpl_out,Fc_wpl_data,FList=[wC_in,Fh_in,wA_in,Ta_in,Ah_in,Cc_in,ps_in],Descr='WPL corrected Fc',Units='mg/m2/s')
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='WPLFlag') and cf['General']['WPLFlag'] == 'True':
        testseries,f = qcutils.GetSeriesasMA(ds,Fc_wpl_out)
        mask = numpy.ma.getmask(testseries)
        index = numpy.where(mask.astype(int)==1)
        ds.series[Fc_wpl_out]['Flag'][index] = 14
    else:
        testseries,f = qcutils.GetSeriesasMA(ds,Fc_wpl_out)
        mask = numpy.ma.getmask(testseries)
        index = numpy.where((numpy.mod(f,10)==0) & (mask.astype(int)==1))    # find the elements with flag = 0, 10, 20 etc and masked (check for masked data with good data flag)
        ds.series[Fc_wpl_out]['Flag'][index] = 14

def Fe_WPL(cf,ds,Fe_wpl_out='Fe',Fe_raw_in='Fe',Fh_in='Fh',Ta_in='Ta',Ah_in='Ah',ps_in='ps'):
    """
        Apply Webb, Pearman and Leuning correction to vapour flux.  This
        correction is necessary to account for flux effects on density
        measurements.  Original formulation: Campbell Scientific
        
        Usage qcts.Fe_WPL(ds,Fe_wpl_out,Fe_raw_in,Fh_in,Ta_in,Ah_in,ps_in)
        ds: data structure
        Fe_wpl_out: output corrected water vapour flux variable to ds.  Example: 'Fe_wpl'
        Fe_raw_in: input water vapour flux in ds.  Example: 'Fe_raw'
        Fh_in: input sensible heat flux in ds.  Example: 'Fh_rv'
        Ta_in: input air temperature in ds.  Example: 'Ta_EC'
        Ah_in: input absolute humidity in ds.  Example: 'Ah_EC'
        ps_in: input atmospheric pressure in ds.  Example: 'ps'
        
        Used for fluxes that are raw or rotated.
        
        Pre-requisite: CalculateFluxes, CalculateFluxes_Unrotated or CalculateFluxesRM
        Pre-requisite: FhvtoFh
        
        Accepts meteorological constants or variables
        """
    log.info(' Applying WPL correction to Fe')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='EWPL'):
        Eargs = ast.literal_eval(cf['FunctionArgs']['EWPL'])
        Fe_wpl_out = Eargs[0]
        Fe_raw_in = Eargs[1]
        Fh_in = Eargs[2]
        Ta_in = Eargs[3]
        Ah_in = Eargs[4]
        ps_in = Eargs[5]
    Fe_raw,f = qcutils.GetSeriesasMA(ds,Fe_raw_in)
    Fh,f = qcutils.GetSeriesasMA(ds,Fh_in)
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_in)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_in)
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    Cpm,f = qcutils.GetSeriesasMA(ds,'Cpm')
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
    rhod,f = qcutils.GetSeriesasMA(ds,'rhod')
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    nRecs = numpy.size(Fh)
    Fe_wpl_flag = numpy.zeros(nRecs,int)
    Ah = Ah/float(1000)                       # Absolute humidity from g/m3 to kg/m3
    sigma_wpl = Ah/rhod
    h2o_wpl_Fe = 1.61*sigma_wpl*Fe_raw
    h2o_wpl_Fh = (1+(1.61*sigma_wpl))*Ah*Lv*(Fh/(rhom*Cpm))/(Ta+273.15)
    Fe_wpl_data = Fe_raw+h2o_wpl_Fe+h2o_wpl_Fh
    qcutils.CreateSeries(ds,Fe_wpl_out,Fe_wpl_data,FList=[Fe_raw_in,Fh_in,Ta_in,Ah_in,ps_in],Descr='WPL corrected Fe',Units='W/m2',Standard='surface_upward_latent_heat_flux')
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='WPLFlag') and cf['General']['WPLFlag'] == 'True':
        testseries,f = qcutils.GetSeriesasMA(ds,Fe_wpl_out)
        mask = numpy.ma.getmask(testseries)
        index = numpy.where(mask.astype(int)==1)
        ds.series[Fe_wpl_out]['Flag'][index] = 14
    else:
        testseries,f = qcutils.GetSeriesasMA(ds,Fe_wpl_out)
        mask = numpy.ma.getmask(testseries)
        index = numpy.where((numpy.mod(f,10)==0) & (mask.astype(int)==1))    # find the elements with flag = 0, 10, 20 etc and masked (check for masked data with good data flag)
        ds.series[Fe_wpl_out]['Flag'][index] = 14

def Fe_WPLcov(cf,ds,Fe_wpl_out='Fe',wA_in='wA',Fh_in='Fh',Ta_in='Ta',Ah_in='Ah',ps_in='ps',wA_out='wA'):
    """
        Apply Webb, Pearman and Leuning correction to vapour flux using the
        original formulation (WPL80).  This correction is necessary to account
        for flux effects on density measurements.  This method uses the
        originally-published formulation using covariances rather than fluxes.
        The difference in the corrected fluxes using the two routines is minor
        and related to scaling the met variables.
        
        Usage qcts.Fe_WPLcov(ds,Fe_wpl_out,wA,Fh,Ta,Ah,ps)
        ds: data structure
        Fe_wpl_out: output corrected water vapour flux to ds.  Example: 'Fe_wpl'
        wA: input covariance(wA) in ds.  Example: 'wAM'
        Fh: input sensible heat flux in ds.  Example: 'Fh_rmv'
        Ta: input air temperature in ds.  Example: 'Ta_HMP'
        Ah: input absolute humidity in ds.  Example: 'Ah_HMP'
        ps: input atmospheric pressure in ds.  Example: 'ps'
        
        Pre-requisite: FhvtoFh
        Pre-requisite: Fe_WPLcov
        
        Accepts meteorological constants or variables
        """
    log.info(' Applying WPL correction to Fe')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='EWPL'):
        Eargs = ast.literal_eval(cf['FunctionArgs']['EWPL'])
        Fe_wpl_out = Eargs[0]
        wA_in = Eargs[1]
        Fh_in = Eargs[2]
        Ta_in = Eargs[3]
        Ah_in = Eargs[4]
        ps_in = Eargs[5]
        wA_out = Eargs[6]
    wA,f = qcutils.GetSeriesasMA(ds,wA_in)
    Fh,f = qcutils.GetSeriesasMA(ds,Fh_in)
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_in)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_in)
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
    rhod,f = qcutils.GetSeriesasMA(ds,'rhod')
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    Cpm,f = qcutils.GetSeriesasMA(ds,'Cpm')
    nRecs = numpy.size(wA)
    TaK = Ta + 273.15
    Ah = Ah/float(1000)                       # Absolute humidity from g/m3 to kg/m3
    sigma_wpl = Ah/rhod
    wT = Fh / (rhom * Cpm)
    Fe_wpl_data = (Lv / 1000) * (1 + (1.61 * sigma_wpl)) * (wA + ((Ah / TaK) * wT))
    wAwpl = Fe_wpl_data * 1000 / Lv
    qcutils.CreateSeries(ds,Fe_wpl_out,Fe_wpl_data,FList=[wA_in,Fh_in,Ta_in,Ah_in,ps_in],Descr='WPL corrected Fe',Units='W/m2',Standard='surface_upward_latent_heat_flux')
    qcutils.CreateSeries(ds,wA_out,wAwpl,FList=[wA_in,Fh_in,Ta_in,Ah_in,ps_in],Descr='WPL corrected Cov(wA)',Units='g/(m2 s)')
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='WPLFlag') and cf['General']['WPLFlag'] == 'True':
        keys = [Fe_wpl_out,wA_out]
        for ThisOne in keys:
            testseries,f = qcutils.GetSeriesasMA(ds,ThisOne)
            mask = numpy.ma.getmask(testseries)
            index = numpy.where(mask.astype(int)==1)
            ds.series[ThisOne]['Flag'][index] = 14
    else:
        keys = [Fe_wpl_out,wA_out]
        for ThisOne in keys:
            testseries,f = qcutils.GetSeriesasMA(ds,ThisOne)
            mask = numpy.ma.getmask(testseries)
            index = numpy.where((numpy.mod(f,10)==0) & (mask.astype(int)==1))    # find the elements with flag = 0, 10, 20 etc and masked (check for masked data with good data flag)
            ds.series[Fe_wpl_out]['Flag'][index] = 14

def FhvtoFh(cf,ds,Ta_in='Ta',Fh_in='Fh',Tv_in='Tv_CSAT',Fe_in='Fe',ps_in='ps',Ah_in='Ah',Fh_out='Fh',attr='Fh rotated and converted from virtual heat flux'):
    """
        Corrects sensible heat flux calculated on the covariance between w'
        and theta', deviations in vertical windspeed and sonically-derived
        virtual temperature.  Uses the formulation developed by Ed Swiatek,
        Campbell Scientific and located in the open path eddy covariance manual.
        
        Usage qcts.FhvtoFh(ds,Ta_in,Fh_in,Tv_in,Fe_in,ps_in,Ah_in,Fh_out,attr)
        ds: data structure
        Ta_in: input air temperature in ds.  Example: 'Ta_HMP'
        Fh_in: input sensible heat flux in ds.  Example: 'Fh'
        Tv_in: input sonic virtual temperature in ds.  Example: 'Tv_CSAT'
        Fe_in: input water vapour flux in ds.  Example: 'Fe_raw'
        ps_in: input atmospheric pressure in ds.  Example: 'ps'
        Ah_in: input absolute pressure in ds.  Example: 'Ah_EC'
        Fh_out: output corrected sensible heat flux to ds.  Example: 'Fh_rv'
        attr: attribute field for variable meta-data in ds.  Example: 'Fh rotated and converted from virtual heat flux'
        
        Typically used following:
            CoordRotation, MassmanApprox, Massman, CalculateFluxesRM (recommended)
            or
            CoordRotation, CalculateFluxes
            or
            CalculateFluxes_Unrotated
        
        Accepts meteorological constants or variables
        """
    log.info(' Converting virtual Fh to Fh')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='FhvtoFhArgs'):
        args = ast.literal_eval(cf['FunctionArgs']['FhvtoFhArgs'])
        Ta_in = args[0]
        Fh_in = args[1]
        Tv_in = args[2]
        Fe_in = args[3]
        ps_in = args[4]
        Ah_in = args[5]
        Fh_out = args[6]
        attr = args[7]
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_in)
    Fh,f = qcutils.GetSeriesasMA(ds,Fh_in)
    Tv,f = qcutils.GetSeriesasMA(ds,Tv_in)
    Fe,f = qcutils.GetSeriesasMA(ds,Fe_in)
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_in)
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    Cpm,f = qcutils.GetSeriesasMA(ds,'Cpm')
    nRecs = len(Fh)
    psPa = ps * 1000
    TaK = Ta + c.C2K
    TvK = Tv + c.C2K
    Fh_o = (TaK / TvK) * (Fh - (rhom * Cpm * ((0.51 * c.Rd * (TaK ** 2)) / psPa) * (Fe / Lv)))
    
    qcutils.CreateSeries(ds,Fh_out,Fh_o,FList=[Ta_in, Fh_in, Tv_in, Fe_in, ps_in, Ah_in], 
                         Descr=attr, Units='W/m2',Standard='surface_upward_sensible_heat_flux')
    testseries = qcutils.GetSeriesasMA(ds,Fh_out)
    mask = numpy.ma.getmask(testseries)
    index = numpy.where(mask.astype(int)==1)
    ds.series[Fh_out]['Flag'][index] = 13

def FilterFcByUstar(cf, ds, Fc_out='Fc', Fc_in='Fc', ustar_in='ustar'):
    """
        Filter the CO2 flux for low ustar periods.  The filtering is done by checking the
        friction velocity for each time period.  If ustar is less than or equal to the
        threshold specified in the control file then the CO2 flux is set to missing.  If
        the ustar is greater than the threshold, no action is taken.  Filtering is not
        done "in place", a new series is created with the label given in the argument Fc_out.
        The QC flag is set to 23 to indicate the Fc value is missing due to low ustar values.
        
        Usage: qcts.FilterFcByUstar(cf, ds, Fc_out, Fc_in, ustar_in)
        cf: control file object    
        ds: data structure
        Fc_out: series label of the corrected CO2 flux
        Fc_in: series label of the uncorrected CO2 flux
        ustar_in: series label of the friction velocity
        
        Parameters loaded from control file:
            ustar_threshold: friction velocity threshold, m/s
        
        """
    log.info(' Filtering CO2 flux based on ustar')
    if qcutils.cfkeycheck(cf,Base='Filters',ThisOne='Fc_in'):
        Fc_in = cf['Filters']['Fc_in']
    
    if qcutils.cfkeycheck(cf,Base='Filters',ThisOne='Fc_out'):
        Fc_out = cf['Filters']['Fc_out']
    
    if qcutils.cfkeycheck(cf,Base='Filters',ThisOne='ustar_in'):
        ustar_in = cf['Filters']['ustar_in']
    
    if qcutils.cfkeycheck(cf,Base='Filters',ThisOne='ustar_threshold'):
        us_threshold = float(cf['Filters']['ustar_threshold'])
    else:
        log.error('FilterFcByUstar: ustar_threshold expected but not found in Filters section of control file')
        return
    
    Fc,Fc_flag = qcutils.GetSeriesasMA(ds,Fc_in,si=0,ei=-1)
    us,us_flag = qcutils.GetSeriesasMA(ds,ustar_in,si=0,ei=-1)
    Fc = numpy.ma.masked_where(us<=us_threshold,Fc)
    index = numpy.where(us<=us_threshold)[0]
    Fc_flag[index] = 18
    descr = ' filtered for low ustar conditions, ustar threshold was '+str(us_threshold)
    units = qcutils.GetUnitsFromds(ds, Fc_in)
    qcutils.CreateSeries(ds,Fc_out,Fc,Flag=Fc_flag,Descr=descr,Units=units)

def footprint_2d(cf,sigmaw,sigmav,ustar,zm,h,znot,r,wd,zeta,L,zc,timestamp,eta,Fc,Fe,level):
    """
        footprint_2d.py
        
        Derive a footprint estimate based on a simple parameterisation
        
        Details see Kljun, N., Calanca, P., Rotach, M.W., Schmid, H.P., 2004:
        Boundary-Layer Meteorology 112, 503-532.
         
        online version: http://footprint.kljun.net
        contact: n.kljun@swansea.ac.uk
        
        Usage: footprint_2d.py <measurement height[m]> <roughness length [m]> <planetary boundary
                              layer height [m]> <sigma_w [m s-1]> <sigma_v [m s-1]> <u* [m s-1]> <r [%]> 
         Output: crosswind integrated footprint: x,f
                 extent of footprint up to r%: xr
                 matrix of 2d footprint: x_2d, y_2d, f_2d
        
         Created: May 15 2012, natascha kljun
         Last change: May 15 2012, nk
        """
    
    # -----------------------------------------------
    # Initialize local variables
    n = 400
    nr = 96
    af = 0.175
    bb = 3.418
    ac = 4.277
    ad = 1.685
    b = 3.69895
    xstep = 0.5
    a3 = 0.08
    k  = 0.4
    sqrt2pi = math.sqrt(2*math.pi)
    a4 = 3.25
    
    lall  = (0.000000, 0.302000, 0.368000, 0.414000, 0.450000,
        0.482000, 0.510000, 0.536000, 0.560000, 0.579999,
        0.601999, 0.621999, 0.639999, 0.657998, 0.675998,
        0.691998, 0.709998, 0.725998, 0.741997, 0.755997,
        0.771997, 0.785997, 0.801997, 0.815996, 0.829996,
        0.843996, 0.857996, 0.871996, 0.885995, 0.899995,
        0.911995, 0.925995, 0.939995, 0.953995, 0.965994,
        0.979994, 0.993994, 1.005994, 1.019994, 1.033994,
        1.045993, 1.059993, 1.073993, 1.085993, 1.099993,
        1.113993, 1.127992, 1.141992, 1.155992, 1.169992,
        1.183992, 1.197991, 1.211991, 1.225991, 1.239991,
        1.253991, 1.269991, 1.283990, 1.299990, 1.315990,
        1.329990, 1.345990, 1.361989, 1.379989, 1.395989,
        1.411989, 1.429989, 1.447988, 1.465988, 1.483988,
        1.501988, 1.521987, 1.539987, 1.559987, 1.581987,
        1.601986, 1.623986, 1.647986, 1.669985, 1.693985,
        1.719985, 1.745984, 1.773984, 1.801984, 1.831983,
        1.863983, 1.895983, 1.931982, 1.969982, 2.009982,
        2.053984, 2.101986, 2.153988, 2.211991, 2.279994,
        2.355998, 2.450002, 2.566008, 2.724015, 2.978027, 
        3.864068)
    
    a = (af/(bb-math.log(znot)))
    c = (ac*(bb-math.log(znot)))
    d = (ad*(bb-math.log(znot)))
    axa = numpy.zeros(n) + a
    bxb = numpy.zeros(n) + b
    cxc = numpy.zeros(n) + c
    dxd = numpy.zeros(n) + d
    zmxzm = numpy.zeros(n) + zm
    sigmawxsigmaw = numpy.zeros(n) + sigmaw
    ustarxustar = numpy.zeros(n) + ustar
    coeff8xcoeff = numpy.zeros(n) + 0.8
    negcoeff8x = numpy.zeros(n) - 0.8
    hxh = numpy.zeros(n) + h
    
    xstar = numpy.ones(n, dtype=float)
    fstar = numpy.ones(n, dtype=float)
    x = numpy.ones(n, dtype=float)
    f_ci = numpy.ones(n, dtype=float)
    
    xstar[0] = -5
    while xstar[0] < -d:
        xstar[0] = xstar[0]+1
    
    for i in range(0, n):
        # Calculate X*
        if i>0:
            xstar[i] = xstar[i-1] + xstep
    
    # Calculate F*
    fstar = axa*((xstar+dxd)/cxc)**bxb * numpy.exp(bxb*(1-(xstar+dxd)/cxc))
    
    # Calculate x and f
    x = xstar * zmxzm * (sigmawxsigmaw/ustar)**(negcoeff8x)
    f_ci = fstar / zmxzm * (1-(zmxzm/hxh)) * (sigmawxsigmaw/ustar)**(coeff8xcoeff)
    
    # Calculate maximum location of influence (peak location)
    xstarmax = c-d
    xmax = xstarmax * zm *(sigmaw/ustar)**(-0.8)
    
    # Get l corresponding to r
    lr = lall[r]
    
    # Calculate distance including R percentage of the footprint
    xstarr = lr*c - d
    xr = xstarr * zm *(sigmaw/ustar)**(-0.8)
    
    if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFile') and cf['Output']['FootprintFile'] == 'True':
        # Calculate lateral dispersion
        u = ustar/k *(math.log(zm/znot) - (zm-znot)/zm)
        tau = numpy.sqrt((x/u)**2 + (a4*(zm-znot)/sigmaw)**2)
        tly = a3*h**2 /((h-zm)*ustar)
        fy_disp = 1/(1 + numpy.sqrt(tau/(2*tly)))
        sigmay = sigmav * tau * fy_disp
        
        x_lim = numpy.max(x)
        y0 = (x[x>0])
        y1 = (y0[y0<=x_lim/2])
        y2 = -(y1[::-1])
        y  = numpy.concatenate((y2,[0],y1))
        
        m = len(y)
        
        y_rot = numpy.reshape(y,(m,1))
        xy = numpy.broadcast_arrays(x, f_ci, sigmay, y_rot)
        if not qcutils.cfkeycheck(cf, Base='Footprint', ThisOne='etaadd'):
            log.error('   Footprint:  CSAT azimuth not provided for coordinate rotation')
            return
        
        x_2d = (xy[0] * numpy.cos(numpy.deg2rad(-eta+float(cf['Footprint']['etaadd'])))) + (xy[3] * numpy.sin(numpy.deg2rad(-eta+float(cf['Footprint']['etaadd']))))   # longitudal rotation of the x,y plane
        y_2d = (xy[3] * numpy.cos(numpy.deg2rad(-eta+45))) - (xy[0] * numpy.sin(numpy.deg2rad(-eta+45)))   # lateral rotation of the x,y plane and axis conversion for wind components
        f_2d = xy[1] * 1/(sqrt2pi*xy[2]) *  numpy.exp(-xy[3]**2 / (2*xy[2]**2))
        
        #x_2d = numpy.zeros((n,m), dtype=float)
        #y_2d = numpy.zeros((n,m), dtype=float)
        #f_2d = numpy.zeros((n,m), dtype=float)
        #for i in range(0, n):
        #    for j in range(0, m):
        #        x_2d[i,j] = (x[i] * numpy.cos(numpy.deg2rad(-eta))) + (y[j] * numpy.sin(numpy.deg2rad(-eta)))   # longitudal rotation of the x,y plane
        #        y_2d[i,j] = -(y[j] * numpy.cos(numpy.deg2rad(-eta))) - (x[i] * numpy.sin(numpy.deg2rad(-eta)))   # lateral rotation of the x,y plane and axis conversion for wind components
        #        f_2d[i,j] = f_ci[i] * 1/(sqrt2pi*sigmay[i]) *  math.exp(-y[j]**2 / (2*sigmay[i]**2))
        #
        fw_c_2d = f_2d * Fc
        fw_e_2d = f_2d * Fe
        STList = []
        if level == 'L3':
            filetext0 = 'Fc'
            filetext1 = 'Fe'
            excltext0 = 'fw_Fc'
            excltext1 = 'fw_Fe'
            excltext3 = 'fc_Fc'
            excltext4 = 'fc_Fe'
        
        if level == 'L4':
            filetext0 = 'GPP'
            filetext1 = 'Re'
            excltext0 = 'fw_GPP'
            excltext1 = 'fw_Re'
            excltext3 = 'fc_GPP'
            excltext4 = 'fc_Re'
        
        for fmt in ['%Y','%m','%d','%H','%M']:
            STList.append(timestamp.strftime(fmt))
            summaryFileName = cf['Files']['Footprint']['FootprintFilePath']+'footprint_2d_summary_'+''.join(STList)+'.xls'
            vectorFileName = cf['Files']['Footprint']['FootprintFilePath']+'footprint_2d_vectors_'+''.join(STList)+'.xls'
            matrixFileName = cf['Files']['Footprint']['FootprintFilePath']+'footprint_2d_matrix_'+''.join(STList)+'.xls'
            vectorFcFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext0+'_w_footprint_2d_vectors_'+''.join(STList)+'.xls'
            matrixFcFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext0+'_w_footprint_2d_matrix_'+''.join(STList)+'.xls'
            vectorFeFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext1+'_w_footprint_2d_vectors_'+''.join(STList)+'.xls'
            matrixFeFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext1+'_w_footprint_2d_matrix_'+''.join(STList)+'.xls'
            vectorFcCFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext0+'_c_footprint_2d_vectors.xls'
            matrixFcCFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext0+'_c_footprint_2d_matrix.xls'
            vectorFeCFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext1+'_c_footprint_2d_vectors.xls'
            matrixFeCFileName = cf['Files']['Footprint']['FootprintFilePath']+filetext1+'_c_footprint_2d_matrix.xls'
        
        if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintSummaryFile') and cf['Output']['FootprintSummaryFile'] == 'True':
            xlFile = xlwt.Workbook()
            xlSheet = xlFile.add_sheet('summary')
            xlCol = 1
            xlRow = 0
            xlSheet.write(xlRow,xlCol,'Measurement height (zm)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,zm)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'Canopy height (zc)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,zc)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'Roughness length (z0)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,znot)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'PBL height (zi)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,h)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'Monin-Obukhov length (L)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,L)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'Stability coefficient (z-d/L, zeta)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,zeta)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'Friction coefficient (ustar)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,ustar)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'sd(w) (sigma_w)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,sigmaw)
            xlRow = xlRow + 1
            xlCol = 1
            xlSheet.write(xlRow,xlCol,'sd(v) (sigma_v)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,sigmav)
            xlRow = xlRow + 1
            xlCol = 1
            if level == 'L3':
                xlSheet.write(xlRow,xlCol,'Fc')
                xlCol = xlCol - 1
                xlSheet.write(xlRow,xlCol,Fc)
                xlRow = xlRow + 1
                xlCol = 1
                xlSheet.write(xlRow,xlCol,'Fe')
                xlCol = xlCol - 1
                xlSheet.write(xlRow,xlCol,Fe)
            elif level == 'L4':
                xlSheet.write(xlRow,xlCol,'GPP')
                xlCol = xlCol - 1
                xlSheet.write(xlRow,xlCol,Fc)
                xlRow = xlRow + 1
                xlCol = 1
                xlSheet.write(xlRow,xlCol,'Re')
                xlCol = xlCol - 1
                xlSheet.write(xlRow,xlCol,Fe)
            
            xlRow = xlRow + 1
            xlCol = 1
            
            xlCol = 3
            xlRow = 0
            xlSheet.write(xlRow,xlCol,'eta')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,eta)
            xlRow = xlRow + 1
            xlCol = 3
            xlSheet.write(xlRow,xlCol,'Wind direction (wd)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,wd)
            xlRow = xlRow + 1
            xlCol = 3
            xlSheet.write(xlRow,xlCol,'% of flux footprint (r)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,r)
            xlRow = xlRow + 1
            xlCol = 3
            xlSheet.write(xlRow,xlCol,'Extent of footprint up to r% (xr)')
            xlCol = xlCol - 1
            xlSheet.write(xlRow,xlCol,xr)
            xlRow = xlRow + 1
            
            xlSheet = xlFile.add_sheet('crosswind_integrated')
            for i in range(0,n):
                xlSheet.write(i,0,x[i])
                xlSheet.write(i,1,f_ci[i])
            
            xlFile.save(summaryFileName)
        
        if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileDataType') and cf['Output']['FootprintFileDataType'] == 'Footprint':
            if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileType') and cf['Output']['FootprintFileType'] == 'Vector':
                footprint_vector_out(vectorFileName,x_2d,y_2d,f_2d,'f')
            
            if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileType') and cf['Output']['FootprintFileType'] == 'Matrix':
                footprint_matrix_out(matrixFileName,x_2d,y_2d,f_2d)
        
        if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileDataType') and cf['Output']['FootprintFileDataType'] == 'Weighted':
            if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileType') and cf['Output']['FootprintFileType'] == 'Vector':
                footprint_vector_out(vectorFcFileName,x_2d,y_2d,fw_c_2d,excltext0)
                footprint_vector_out(vectorFeFileName,x_2d,y_2d,fw_e_2d,excltext1)
            
            if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileType') and cf['Output']['FootprintFileType'] == 'Matrix':
                footprint_matrix_out(matrixFcFileName,x_2d,y_2d,fw_c_2d)
                footprint_matrix_out(matrixFeFileName,x_2d,y_2d,fw_e_2d)
            
        if qcutils.cfkeycheck(cf, Base='Output', ThisOne='FootprintFileDataType') and cf['Output']['FootprintFileDataType'] == 'Climatology':
            filenames = [vectorFcCFileName, matrixFcCFileName, vectorFeCFileName, matrixFeCFileName]
            labels = [excltext3, excltext4]
            return xr, x_2d, y_2d, fw_c_2d, fw_e_2d, filenames, labels

    return xr

def footprint_climatology(fc_c,fc_e,x_2d,y_2d,fw_c,fw_e,n,m,xmin,xmax,ymin,ymax,p):
    
    #x = numpy.arange(xmin+(0.5*p),xmax,p,dtype=float)
    #y = numpy.arange(ymin+(0.5*p),ymax,p,dtype=float)
    #y_rot = numpy.reshape(y,(len(y),1))
    #xy = numpy.broadcast_arrays(x, y_rot)
    #fc_c1 = numpy.zeros((len(fc_c),len(fc_c[0])),dtype=float) + numpy.mean(fw_c[numpy.where((x_2d > xy[0]) & (x_2d < xy[0] + p) & (y_2d > xy[1]) & (y_2d < xy[0] + p))])
    #fc_cindex = numpy.where((fc_c1 != 0) & (fc_c1 != 'nan'))
    #fc_c[fc_cindex] = fc_c[fc_cindex] + fc_c1[fc_cindex]
    #
    x = numpy.arange(xmin+(0.5*p),xmax,p,dtype=float)
    y = numpy.arange(ymin+(0.5*p),ymax,p,dtype=float)
    y_rot = numpy.reshape(y,(len(y),1))
    xy = numpy.broadcast_arrays(x, y_rot)
    ii = 0
    for i in range(int(xmin),int(xmax),int(p)):
        jj = 0
        for j in range(int(ymin),int(ymax),int(p)):
            xindex = numpy.where((x_2d > i) & (x_2d < i + p))
            yindex = numpy.where((y_2d > j) & (y_2d < j + p))
            if (len(xindex[0]) != 0) & (len(yindex[0]) != 0):
                mask = numpy.zeros((len(x_2d),len(y_2d[0])),dtype=int)
                mask[xindex] = 1
                mask[yindex] = mask[yindex] + 1
                maskindex = numpy.where(mask > 1)
                if len(maskindex[0]) != 0:
                    fc_c[jj,ii] = fc_c[jj,ii] + numpy.mean(fw_c[maskindex])
                    fc_e[jj,ii] = fc_e[jj,ii] + numpy.mean(fw_e[maskindex])
            
            jj = jj + 1
        
        ii = ii + 1
    
    return fc_c, fc_e, xy[0], xy[1]

def footprint_matrix_out(filename,x_2d,y_2d,f_2d):
    #matrixout = open(filename, 'w')
    #csvSheet = csv.writer(matrixout, dialect='excel-tab')
    #n = len(x_2d)
    #m = len(x_2d[0])
    #xout = numpy.zeros(n+1,dtype=float)
    #xout[0] = -9999
    #for i in range(0,n):
    #    xout[i+1] = x_2d[i,0]
    #
    #csvSheet.writerow(xout)
    #for j in range(0,m):
    #    yout = y_2d[0,j]
    #    dataout = f_2d[j]
    #    ydataout = numpy.zeros(n+1,dtype=float)
    #    ydataout[0] = yout
    #    for i in range(0,n):
    #        ydataout[i+1] = f_2d[i,j]
    #    
    #    csvSheet.writerow(ydataout)
    #
    #matrixout.close()
    
    n = len(x_2d)
    m = len(x_2d[0])
    out = numpy.zeros((n+1,m+1),dtype=float)
    out[0,0] = -9999
    out[0,1:] = x_2d[0,:]
    out[1:,0] = y_2d[:,0]
    out[1:,1:] = f_2d[:,:]
    numpy.savetxt(filename,out,delimiter='\t')
    
    return

def footprint_vector_out(filename,x_2d,y_2d,f_2d,text):
    #vectorout = open(filename, 'w')
    #csvSheet = csv.writer(vectorout, dialect='excel-tab')
    #csvSheet.writerow(['x','y',text])
    #n = len(x_2d)
    #m = len(x_2d[0])
    #for i in range(0,n):
    #    for j in range(0,m):
    #        csvSheet.writerow([x_2d[i,j],y_2d[i,j],f_2d[i,j]])
    #
    #vectorout.close()
    
    log.info('     '+filename+' cols: x, y, '+text)
    x = numpy.reshape(x_2d,(1,(len(x_2d)*len(x_2d[0]))))
    y = numpy.reshape(y_2d,(1,(len(x_2d)*len(x_2d[0]))))
    f = numpy.reshape(f_2d,(1,(len(x_2d)*len(x_2d[0]))))
    out = numpy.vstack((x,y,f)).T
    numpy.savetxt(filename,out,delimiter='\t')
    
    return

def GapFillFromAlternate(cf,ds,series=''):
    """
        Gap fill using data from alternate sites specified in the control file
        """
    ts = ds.globalattributes['time_step']
    # Gap fill using data from alternate sites specified in the control file
    ds_alt = {}               # create a dictionary for the data from alternate sites
    open_ncfiles = []         # create an empty list of open netCDF files
    if len(series)==0:        # if no series list passed in then ...
        series = cf['Variables'].keys() # ... create one using all variables listed in control file
    # loop over variables listed in the control file
    for ThisOne in series:
        # check that GapFillFromAlternate is specified for this series
        if qcutils.incf(cf,ThisOne) and qcutils.haskey(cf,ThisOne,'GapFillFromAlternate'):
            # loop over the entries in the GapFillFromAlternate section
            for Alt in cf['Variables'][ThisOne]['GapFillFromAlternate'].keys():
                log.info(' Gap filling '+ThisOne+' by replacing with alternate site data')
                # get the file name for the alternate site
                alt_filename = cf['Variables'][ThisOne]['GapFillFromAlternate'][Alt]['FileName']
                # get the variable name for the alternate site data if specified, otherwise use the same name
                if 'AltVarName' in cf['Variables'][ThisOne]['GapFillFromAlternate'][Alt].keys():
                    alt_varname = cf['Variables'][ThisOne]['GapFillFromAlternate'][Alt]['AltVarName']
                else:
                    alt_varname = ThisOne
                # check to see if the alternate site file is already open
                if alt_filename not in open_ncfiles:
                    # open and read the file if it is not already open
                    n = len(open_ncfiles)
                    open_ncfiles.append(alt_filename)
                    ds_alt[n] = qcio.nc_read_series_file(alt_filename)
                else:
                    # get the file index number if it is already open
                    n = open_ncfiles.index(alt_filename)
                # check to see if alternate site data needs transform
                if 'Transform' in cf['Variables'][ThisOne]['GapFillFromAlternate'][Alt].keys():
                    # get the datetime series for the alternate site
                    AltDateTime = ds_alt[n].series['DateTime']['Data']
                    # get the data for the alternate site
                    AltSeriesData = ds_alt[n].series[alt_varname]['Data']
                    # evaluate the list of start dates, end dates and transform coefficients
                    TList = ast.literal_eval(cf['Variables'][ThisOne]['GapFillFromAlternate'][Alt]['Transform'])
                    # loop over the datetime ranges for the transform
                    for TListEntry in TList:
                        qcts.TransformAlternate(TListEntry,AltDateTime,AltSeriesData,ts=ts)
                qcts.ReplaceWhereMissing(ds.series[ThisOne],ds.series[ThisOne],ds_alt[n].series[alt_varname],100)

def GapFillFromClimatology(cf,ds,series=''):
    alt_xlbook = {}
    open_xlfiles = []
    if len(series)==0:        # if no series list passed in then ...
        series = cf['Variables'].keys() # ... create one using all variables listed in control file
    for ThisOne in series:
        if qcutils.incf(cf,ThisOne) and qcutils.haskey(cf,ThisOne,'GapFillFromClimatology'):
            log.info(' Gap filling '+ThisOne+' using climatology')
            Values = numpy.zeros([48,12])
            alt_filename = cf['Variables'][ThisOne]['GapFillFromClimatology']['FileName']
            if alt_filename not in open_xlfiles:
                n = len(open_xlfiles)
                alt_xlbook[n] = xlrd.open_workbook(alt_filename)
                open_xlfiles.append(alt_filename)
            else:
                n = open_xlfiles.index(alt_filename)
            ThisSheet = alt_xlbook[n].sheet_by_name(ThisOne)
            val1d = numpy.zeros_like(ds.series[ThisOne]['Data'])
            for month in range(M1st,M2nd+1):
                xlCol = (month-1)*5 + 2
                Values[:,month-1] = ThisSheet.col_values(xlCol)[2:50]
            for i in range(len(ds.series[ThisOne]['Data'])):
                h = numpy.int(2*ds.series['Hdh']['Data'][i])
                m = numpy.int(ds.series['Month']['Data'][i])
                val1d[i] = Values[h,m-1]
            index = numpy.where(abs(ds.series[ThisOne]['Data']-float(-9999))<c.eps)[0]
            ds.series[ThisOne]['Data'][index] = val1d[index]
            ds.series[ThisOne]['Flag'][index] = 40

def GapFillFromRatios(cf,ds):
    nRecs = int(ds.globalattributes['NumRecs'])
    ndays = 365
    Year = ds.series['Year']['Data'][0]
    if isleap(Year): ndays = 366
    log.info(' GapFillFromRatios: ndays='+ndays)
    # get local versions of the series required as masked arrays
    # - we use masked arrays here to simplify subsequent calculations
    Fn,f = qcutils.GetSeriesasMA(ds,'Fn')         # net radiation
    Fg,f = qcutils.GetSeriesasMA(ds,'Fg')         # ground heat flux
    Fa = Fn - Fg                                  # available energy
    # get local copies of series required as non-masked arrays
    Fh = ds.series['Fh']['Data']
    Fe = ds.series['Fe']['Data']
    Fc = ds.series['Fc']['Data']
    for ThisOne in ['Fe','Fh','Fc']:
        alt_filename = cf['Variables'][ThisOne]['GapFillUsingRatios']['FileName']
        alt_xlbook = xlrd.open_workbook(alt_filename)
        xl_sheetname = cf['Variables'][ThisOne]['GapFillUsingRatios']['xlSheet']
        xlsheet = alt_xlbook.sheet_by_name(xl_sheetname)
        ratio = numpy.zeros((48,12))
        for xlCol in range(12):
            ratio[:,xlCol] = xlsheet.col_values(xlCol+1)[1:49]

        r3d = numpy.tile(ratio,(3,3))
        nx = numpy.shape(r3d)[1]
        nxi = ndays*3
        ny = numpy.shape(r3d)[0]
        nyi = numpy.shape(r3d)[0]
        x = numpy.linspace(1,nx,nx)
        y = numpy.linspace(1,ny,ny)
        xi = numpy.linspace(1,nx,nxi)
        yi = numpy.linspace(1,ny,nyi)

        nk = interpolate.RectBivariateSpline(y,x,r3d,kx=2,ky=2)
        r3di = nk(yi,xi)
        ri = r3di[nyi/3:2*nyi/3,nxi/3:2*nxi/3]
        ratio1d = numpy.ravel(ri,order='F')

        #ratio1d = numpy.zeros(nRecs)
        #for i in range(len(ds.series['Month']['Data'])):
            #h = numpy.int(2*ds.series['Hdh']['Data'][i])
            #m = numpy.int(ds.series['Month']['Data'][i])
            #ratio1d[i] = ratio[h,m-1]

        if ThisOne=='Fe':
            log.info(' Gap filling Fe using EF')
            Fe_gf = ratio1d * Fa                  # latent heat flux from evaporative fraction
            Fe_gf = numpy.ma.filled(Fe_gf,float(-9999))
            index = numpy.where((abs(Fe-float(-9999))<c.eps)&(abs(Fe_gf-float(-9999))>c.eps))
            ds.series['Fe']['Data'][index] = Fe_gf[index]
            ds.series['Fe']['Flag'][index] = 50
            qcutils.CreateSeries(ds,'EF',ratio1d,FList=['Fn'],Descr='Evaporative fraction',Units='none')
            qcutils.CreateSeries(ds,'Fe_gf',Fe_gf,FList=['Fe'],Descr='Fe gap filled using EF',Units='W/m2',Standard='surface_upward_latent_heat_flux')
        if ThisOne=='Fh':
            log.info(' Gap filling Fh using BR')
            Fh_gf = ratio1d * Fe_gf               # sensible heat flux from Bowen ratio
            Fh_gf = numpy.ma.filled(Fh_gf,float(-9999))
            index = numpy.where((abs(Fh-float(-9999))<c.eps)&(abs(Fh_gf-float(-9999))>c.eps))
            ds.series['Fh']['Data'][index] = Fh_gf[index]
            ds.series['Fh']['Flag'][index] = 50
            qcutils.CreateSeries(ds,'BR',ratio1d,FList=['Fn'],Descr='Bowen ratio',Units='none')
        if ThisOne =='Fc':
            log.info(' Gap filling Fc using WUE')
            Fc_gf = ratio1d * Fe_gf               # CO2 flux from ecosystem water use efficiency
            Fc_gf = numpy.ma.filled(Fc_gf,float(-9999))
            index = numpy.where((abs(Fc-float(-9999))<c.eps)&(abs(Fc_gf-float(-9999))>c.eps))
            ds.series['Fc']['Data'][index] = Fc_gf[index]
            ds.series['Fc']['Flag'][index] = 50
            qcutils.CreateSeries(ds,'WUE',ratio1d,FList=['Fn'],Descr='Water use efficiency',Units='none')

def get_averages(Data):
    """
        Get daily averages on days when no 30-min observations are missing.
        Days with missing observations return a value of -9999
        Values returned are sample size (Num) and average (Av)
        
        Usage qcts.get_averages(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(-9999))>c.eps)
    Num = numpy.size(li)
    if Num == 0:
        Av = -9999
    elif Num == 48:
        Av = numpy.ma.mean(Data[li])
    else:
        x = 0
        index = numpy.ma.where(Data.mask == True)[0]
        if len(index) == 1:
            x = 1
        elif len(index) > 1:
            for i in range(len(Data)):
                if Data.mask[i] == True:
                    x = x + 1
        
        if x == 0:
            Av = numpy.ma.mean(Data[li])
        else:
            Av = -9999
    return Num, Av

def get_canopyresistance(cf,ds,Uavg,uindex,PMin,Level,critFsd,critFe):
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='zm'):
        zm = float(cf['PenmanMonteith']['zm'])
    
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='z0'):
        z0m = float(cf['PenmanMonteith']['z0'])
    
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='zc'):
        zc = float(cf['PenmanMonteith']['zc'])
    
    Fe,f = qcutils.GetSeriesasMA(ds,PMin[0])
    Ta,f = qcutils.GetSeriesasMA(ds,PMin[1])
    Ah,f = qcutils.GetSeriesasMA(ds,PMin[2])
    ps,f = qcutils.GetSeriesasMA(ds,PMin[3])
    Fn,f = qcutils.GetSeriesasMA(ds,PMin[5])
    Fsd,f = qcutils.GetSeriesasMA(ds,PMin[6])
    Fg,f = qcutils.GetSeriesasMA(ds,PMin[7])
    flagList = [PMin[0],PMin[1],PMin[2],PMin[3],PMin[4],PMin[5],PMin[6],PMin[7]]
    VPD,f = qcutils.GetSeriesasMA(ds,'VPD')
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    Cpm,f = qcutils.GetSeriesasMA(ds,'Cpm')
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
    gamma = mf.gamma(ps,Cpm,Lv)
    delta = mf.delta(Ta)
    if 'gamma' not in ds.series.keys():
        qcutils.CreateSeries(ds,'gamma',gamma,FList=[PMin[3],'Cpm','Lv'],Descr='Psychrometric coefficient',Units='kPa/C')
    
    if 'delta' not in ds.series.keys():
        qcutils.CreateSeries(ds,'delta',delta,FList=[PMin[1]],Descr='Slope of the saturation vapour pressure v temperature curve',Units='kPa/C')
    
    Feindex = numpy.ma.where(Fe < critFe)[0]
    Fsdindex = numpy.ma.where(Fsd < critFsd)[0]
    #Fnindex = numpy.where(Fn < 0)[0]
    z0v = 0.1 * z0m
    d = (2 / 3) * zc
    ra = (numpy.log((zm - d) / z0m) * numpy.log((zm - d) / z0v)) / (((c.k) ** 2) * Uavg)
    rc = ((((((delta * (Fn - Fg) / (Lv)) + (rhom * Cpm * (VPD / ((Lv) * ra)))) / (Fe / (Lv))) - delta) / gamma) - 1) * ra
    rcindex = numpy.ma.where(rc < 0)[0]
    Gc = (1 / rc) * (Ah * 1000) / 18
    qcutils.CreateSeries(ds,'ram',ra,FList=flagList,Descr='Aerodynamic resistance from drag coefficient, Allen/Jensen formulation, '+Level,Units='s/m')
    qcutils.CreateSeries(ds,'rC',rc,FList=flagList,Descr='Canopy resistance from Penman-Monteith inversion, Allen/Jensen formulation, '+Level,Units='s/m')
    qcutils.CreateSeries(ds,'GC',Gc,FList=flagList,Descr='Canopy conductance from Penman-Monteith inversion, Allen/Jensen formulation, '+Level,Units='mmolH2O/(m2ground s)')
    
    Label = ['ram','rC','GC']
    for listindex in range(0,3):
        ds.series[Label[listindex]]['Attr']['InputSeries'] = PMin
        ds.series[Label[listindex]]['Attr']['FsdCutoff'] = critFsd
        ds.series[Label[listindex]]['Attr']['FeCutoff'] = critFe
        ds.series[Label[listindex]]['Flag'][rcindex] = 131
        ds.series[Label[listindex]]['Flag'][uindex] = 134
        ds.series[Label[listindex]]['Flag'][Feindex] = 132
        ds.series[Label[listindex]]['Flag'][Fsdindex] = 133
        ds.series[Label[listindex]]['Data'][rcindex] = numpy.float64(-9999)
        ds.series[Label[listindex]]['Data'][uindex] = numpy.float64(-9999)
        ds.series[Label[listindex]]['Data'][Feindex] = numpy.float64(-9999)
        ds.series[Label[listindex]]['Data'][Fsdindex] = numpy.float64(-9999)
    
    return

def get_leafresistance(cf,ds,rinverted):
    Fsd,Fsd_flag = qcutils.GetSeriesasMA(ds,'Fsd')
    Hdh,f = qcutils.GetSeriesasMA(ds,'Hdh')
    Day,f = qcutils.GetSeriesasMA(ds,'Day')
    Month,f = qcutils.GetSeriesasMA(ds,'Month')
    nRecs = len(Fsd)
    if 'LAI' not in ds.series.keys():
        log.info('  Penman-Monteith: integrating daily LAI file into data structure')
        InLevel = 'L4LAI'
        OutLevel = 'L4LAI'
        qcio.autoxl2nc(cf,InLevel,OutLevel)
        dsLAI = qcio.nc_read_series(cf,'L4LAI')
        LAI,fd = qcutils.GetSeriesasMA(dsLAI,'LAI')
        Day_LAI,fd = qcutils.GetSeriesasMA(dsLAI,'Day')
        Month_LAI,fd = qcutils.GetSeriesasMA(dsLAI,'Month')
        nDays = len(LAI)
        LAI_expanded = numpy.ma.zeros(nRecs,float)
        Night = numpy.ma.zeros(nRecs)
        LAI_flag = numpy.ma.zeros(nRecs,int)
        
        for i in range(nRecs):
            if Month[i] == 1 or Month[i] == 3 or Month[i] == 5 or Month[i] == 7 or Month[i] == 8 or Month[i] == 10 or Month[i] == 12:
                dRan = 31
            if Month[i] == 2:
                if ds.series['Year']['Data'][0] % 4 == 0:
                    dRan = 29
                else:
                    dRan = 28
            if Month[i] == 4 or Month[i] == 6 or Month[i] == 9 or Month[i] == 11:
                dRan = 30
                
            Night[i] = Day[i]
        
        log.info(' Penman-Monteith: filling LAI from daily LAI')
        for z in range(nDays):
            for i in range(nRecs):
                if Night[i] == Day_LAI[z]:
                    if Month[i] == Month_LAI[z]:
                        LAI_expanded[i] = LAI[z]
                        LAI_flag[i] = dsLAI.series['LAI']['Flag'][z]
        
        qcutils.CreateSeries(ds,'LAI',LAI_expanded,Flag=0,Descr='Leaf area index, spline-fit interpolation from MODIS product',Units='m2/m2')
        ds.series['LAI']['Flag'] = LAI_flag
    else:
        LAI_expanded, LAI_flag = qcutils.GetSeriesasMA(ds,'LAI')
    
    log.info('  Penman-Monteith: computing leaf resistance from inversion surface resistance and LAI')
    rCin, rc_flag = qcutils.GetSeriesasMA(ds,rinverted)
    rl = rCin * 0.5 * LAI_expanded
    rl_flag = numpy.zeros(nRecs,float)
    Fsd_index = numpy.where(Fsd < 600)[0]
    Fsd2_index = numpy.where(numpy.mod(Fsd_flag,10)!=0)[0]
    rC_index = numpy.where(numpy.mod(rc_flag,10)!=0)[0]
    LAI_index = numpy.where(numpy.mod(LAI_flag,10)!=0)[0]
    rl[Fsd_index] = float(-9999)
    rl_flag[Fsd_index] = 133
    rl[Fsd2_index] = float(-9999)
    rl_flag[Fsd2_index] = Fsd_flag[Fsd2_index]
    rl[rC_index] = float(-9999)
    rl_flag[rC_index] = rc_flag[rC_index]
    rl[LAI_index] = float(-9999)
    rl_flag[LAI_index] = LAI_flag[LAI_index]
    return rl, rl_flag

def get_minmax(Data):
    """
        Get daily minima and maxima on days when no 30-min observations are missing.
        Days with missing observations return a value of -9999
        Values returned are sample size (Num), minimum (Min) and maximum (Max)
        
        Usage qcts.get_minmax(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(-9999))>c.eps)
    Num = numpy.size(li)
    if Num == 0:
        Min = -9999
        Max = -9999
    elif Num == 48:
        Min = numpy.ma.min(Data[li])
        Max = numpy.ma.max(Data[li])
    else:
        x = 0
        index = numpy.ma.where(Data.mask == True)[0]
        if len(index) == 1:
            x = 1
        elif len(index) > 1:
            for i in range(len(Data)):
                if Data.mask[i] == True:
                    x = x + 1
        
        if x == 0:
            Min = numpy.ma.min(Data[li])
            Max = numpy.ma.max(Data[li])
        else:
            Min = -9999
            Max = -9999
    return Num, Min, Max

def get_nightsums(Data):
    """
        Get nightly sums and averages on nights when no 30-min observations are missing.
        Nights with missing observations return a value of -9999
        Values returned are sample size (Num), sums (Sum) and average (Av)
        
        Usage qcts.get_nightsums(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(Data.mask == False)[0]
    Num = numpy.size(li)
    if Num == 0:
        Sum = -9999
        Av = -9999
    else:
        x = 0
        for i in range(len(Data)):
            if Data.mask[i] == True:
                x = x + 1
        
        if x == 0:
            Sum = numpy.ma.sum(Data[li])
            Av = numpy.ma.mean(Data[li])
        else:
            Sum = -9999
            Av = -9999
    
    return Num, Sum, Av

def get_rav(cf,ds,Uavg,PMin,qList,layer='',method='Cemethod'):
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne=method):
        if method == 'Ce_2layer' and layer == '':
            bothlayers = 'True'
            layer = 'base_'
        else:
            bothlayers = 'False'
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne=layer+'zq_low'):
            zq_low = float(cf['PenmanMonteith'][layer+'zq_low'])
        else:
            log.error('  PenmanMonteith:  zq_low (height of lower q sensor) not given')
            return
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne=layer+'zq_surface'):
            zq_surface = float(cf['PenmanMonteith'][layer+'zq_surface'])
        else:
            log.error('  PenmanMonteith:  zq_surface (height of q_surface extrapolation target) not given')
            return
        
        if bothlayers == 'True':
            layer = 'top_'
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne=layer+'zq_high'):
            zq_high = float(cf['PenmanMonteith'][layer+'zq_high'])
        else:
            log.error('  PenmanMonteith:  zq_high (height of upper q sensor) not given')
            return
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne=layer+'zq_air'):
            zq_air = float(cf['PenmanMonteith'][layer+'zq_air'])
        else:
            log.error('  PenmanMonteith:  zq_air (height of q_air extrapolation target) not given')
            return
        
        if bothlayers == 'True':
            layer = 'full_'
        
        log.info('   Ce method:  '+layer+'zq_high: '+str(zq_high)+', '+layer+'zq_low: '+str(zq_low))
        log.info('   Ce method:  '+layer+'zq_air: '+str(zq_air)+', '+layer+'zq_surface: '+str(zq_surface))
        q_high,fqh = qcutils.GetSeriesasMA(ds,qList[0])
        q_low,fql = qcutils.GetSeriesasMA(ds,qList[1])
        if zq_low == 0:
            qsurface = numpy.zeros(len(q_low), dtype=float) + q_low
        elif zq_low == zq_surface:
            qsurface = numpy.zeros(len(q_low), dtype=float) + q_low
        else:
            qsurface = extrapolate_humidity(zq_surface,zq_high,zq_low,q_high,q_low,fqh,fql)
        
        if zq_high == zq_air:
            qair = numpy.zeros(len(q_high), dtype=float) + q_high
        else:
            qair = extrapolate_humidity(zq_air,zq_high,zq_low,q_high,q_low,fqh,fql)
        
    Fe,f = qcutils.GetSeriesasMA(ds,PMin[0])
    Ta,f = qcutils.GetSeriesasMA(ds,PMin[1])
    Ah,f = qcutils.GetSeriesasMA(ds,PMin[2])
    ps,f = qcutils.GetSeriesasMA(ds,PMin[3])
    Fn,f = qcutils.GetSeriesasMA(ds,PMin[5])
    Fsd,f = qcutils.GetSeriesasMA(ds,PMin[6])
    Fg,f = qcutils.GetSeriesasMA(ds,PMin[7])
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    Ce = mf.bulktransfercoefficient(Fe,Lv,Uavg,qair,qsurface)
    rav = mf.aerodynamicresistance(Uavg,Ce)
    ravindex = numpy.ma.where(rav < 0)[0]
    rav[ravindex] = numpy.float(-9999)
    return Ce, rav, ravindex

def get_rstGst(cf,ds,PMin,rav):
    Fe,f = qcutils.GetSeriesasMA(ds,PMin[0])
    Ta,f = qcutils.GetSeriesasMA(ds,PMin[1])
    Ah,f = qcutils.GetSeriesasMA(ds,PMin[2])
    ps,f = qcutils.GetSeriesasMA(ds,PMin[3])
    Fn,f = qcutils.GetSeriesasMA(ds,PMin[5])
    Fsd,f = qcutils.GetSeriesasMA(ds,PMin[6])
    Fg,f = qcutils.GetSeriesasMA(ds,PMin[7])
    VPD,f = qcutils.GetSeriesasMA(ds,'VPD')
    Lv,f = qcutils.GetSeriesasMA(ds,'Lv')
    Cpm,f = qcutils.GetSeriesasMA(ds,'Cpm')
    rhom,f = qcutils.GetSeriesasMA(ds,'rhom')
    gamma = mf.gamma(ps,Cpm,Lv)
    delta = mf.delta(Ta)
    if 'gamma' not in ds.series.keys():
        qcutils.CreateSeries(ds,'gamma',gamma,FList=[PMin[3],'Cpm','Lv'],Descr='Psychrometric coefficient',Units='kPa/C')
    
    if 'delta' not in ds.series.keys():
        qcutils.CreateSeries(ds,'delta',delta,FList=[PMin[1]],Descr='Slope of the saturation vapour pressure v temperature curve',Units='kPa/C')
    
    rst = ((((((delta * (Fn - Fg) / (Lv)) + (rhom * Cpm * (VPD / ((Lv) * rav)))) / (Fe / (Lv))) - delta) / gamma) - 1) * rav
    rstindex = numpy.ma.where(rst < 0)[0]
    Gst = (1 / rst) * (Ah * 1000) / 18
    Gstindex = numpy.ma.where(Gst < 0)[0]
    return rst, rstindex, Gst, Gstindex

def get_soilaverages(Data):
    """
        Get daily averages of soil water content on days when 15 or fewer 30-min observations are missing.
        Days with 16 or more missing observations return a value of -9999
        Values returned are sample size (Num) and average (Av)
        
        Usage qcts.get_soilaverages(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(-9999))>c.eps)
    Num = numpy.size(li)
    if Num > 33:
        Av = numpy.ma.mean(Data[li])
    else:
        Av = -9999
    return Num, Av

def get_subsums(Data):
    """
        Get separate daily sums of positive and negative fluxes when no 30-min observations are missing.
        Days with missing observations return a value of -9999
        Values returned are positive and negative sample sizes (PosNum and NegNum) and sums (SumPos and SumNeg)
        
        Usage qcts.get_subsums(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(-9999))>c.eps)
    Num = numpy.size(li)
    if Num == 48:
        pi = numpy.ma.where(Data[li]>0)
        ni = numpy.ma.where(Data[li]<0)
        PosNum = numpy.size(pi)
        NegNum = numpy.size(ni)
        if PosNum > 0:
            SumPos = numpy.ma.sum(Data[pi])
        else:
            SumPos = 0
        if NegNum > 0:
            SumNeg = numpy.ma.sum(Data[ni])
        else:
            SumNeg = 0
    else:
        pi = numpy.ma.where(Data[li]>0)
        ni = numpy.ma.where(Data[li]<0)
        PosNum = numpy.size(pi)
        NegNum = numpy.size(ni)
        SumPos = -9999
        SumNeg = -9999
    return PosNum, NegNum, SumPos, SumNeg

def get_sums(Data):
    """
        Get daily sums when no 30-min observations are missing.
        Days with missing observations return a value of -9999
        Values returned are sample size (Num) and sum (Sum)
        
        Usage qcts.get_sums(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(-9999))>c.eps)
    Num = numpy.size(li)
    if Num == 0:
        Sum = -9999
    elif Num == 48:
        Sum = numpy.ma.sum(Data[li])
    else:
        x = 0
        index = numpy.ma.where(Data.mask == True)[0]
        if len(index) == 1:
            x = 1
        elif len(index) > 1:
            for i in range(len(Data)):
                if Data.mask[i] == True:
                    x = x + 1
        
        if x == 0:
            Sum = numpy.ma.sum(Data[li])
        else:
            Sum = -9999
    return Num, Sum

def get_qcflag(ds):
    """
        Set up flags during ingest of L1 data.
        Identifies missing observations as -9999 and sets flag value 1
        
        Usage qcts.get_qcflag(ds)
        ds: data structure
        """
    log.info(' Setting up the QC flags')
    nRecs = len(ds.series['xlDateTime']['Data'])
    for ThisOne in ds.series.keys():
        if ThisOne not in ['xlDateTime','Year','Month','Day','Hour','Minute','Second','Hdh']:
            ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,dtype=int)
            index = numpy.where(ds.series[ThisOne]['Data']==float(-9999))
            ds.series[ThisOne]['Flag'][index] = 1

def get_yearmonthdayhourminutesecond(cf,ds):
    """
        Gets year, month, day, hour, and if available seconds, from
        excel-formatted Timestamp
        
        Usage qcts.get_yearmonthdayhourminutesecond(cf,ds)
        cf: control file
        ds: data structure
        """
    log.info(' Getting date and time variables')
    # set the date mode for PC or MAC versions of Excel dates
    datemode = 0
    if cf['General']['Platform'] == 'Mac': datemode = 1
    nRecs = len(ds.series['xlDateTime']['Data'])
    Year = numpy.array([-9999]*nRecs,numpy.int32)
    Month = numpy.array([-9999]*nRecs,numpy.int32)
    Day = numpy.array([-9999]*nRecs,numpy.int32)
    Hour = numpy.array([-9999]*nRecs,numpy.int32)
    Minute = numpy.array([-9999]*nRecs,numpy.int32)
    Second = numpy.array([-9999]*nRecs,numpy.int32)
    Hdh = numpy.array([-9999]*nRecs,numpy.float64)
    Ddd = numpy.array([-9999]*nRecs,numpy.float64)
    flag = numpy.zeros(nRecs)
    for i in range(nRecs):
        DateTuple = xlrd.xldate_as_tuple(ds.series['xlDateTime']['Data'][i],datemode)
        Year[i] = int(DateTuple[0])
        Month[i] = int(DateTuple[1])
        Day[i] = int(DateTuple[2])
        Hour[i] = int(DateTuple[3])
        Minute[i] = int(DateTuple[4])
        Second[i] = int(DateTuple[5])
        Hdh[i] = float(DateTuple[3])+float(DateTuple[4])/60.
        Ddd[i] = ds.series['xlDateTime']['Data'][i] - xlrd.xldate.xldate_from_date_tuple((Year[i],1,1),datemode)
    qcutils.CreateSeries(ds,'Year',Year,Flag=flag,Descr='Year',Units='none')
    qcutils.CreateSeries(ds,'Month',Month,Flag=flag,Descr='Month',Units='none')
    qcutils.CreateSeries(ds,'Day',Day,Flag=flag,Descr='Day',Units='none')
    qcutils.CreateSeries(ds,'Hour',Hour,Flag=flag,Descr='Hour',Units='none')
    qcutils.CreateSeries(ds,'Minute',Minute,Flag=flag,Descr='Minute',Units='none')
    qcutils.CreateSeries(ds,'Second',Second,Flag=flag,Descr='Second',Units='none')
    qcutils.CreateSeries(ds,'Hdh',Hdh,Flag=flag,Descr='Decimal hour of the day',Units='none')
    qcutils.CreateSeries(ds,'Ddd',Ddd,Flag=flag,Descr='Decimal day of the year',Units='none')

def InvertSign(ds,ThisOne):
    log.info(' Inverting sign of '+ThisOne)
    index = numpy.where(abs(ds.series[ThisOne]['Data']-float(-9999))>c.eps)[0]
    ds.series[ThisOne]['Data'][index] = float(-1)*ds.series[ThisOne]['Data'][index]

def InterpolateOverMissing(cf,ds,series='',maxlen=1000):
    if len(series)==0:
        series = cf['InterpolateVars'].keys() # ... create one using all variables listed in control file
    #print time.strftime('%X')+' Interpolating over missing values in series '+S_in
    DateNum = date2num(ds.series['DateTime']['Data'])
    for ThisOne in series:
        if ThisOne in ds.series.keys():
            iog = numpy.where(ds.series[ThisOne]['Data']!=float(-9999))[0]            # index of good values
            if len(iog) > 0:
                f = interpolate.interp1d(DateNum[iog],ds.series[ThisOne]['Data'][iog])    # linear interpolation function
                iom = numpy.where((ds.series[ThisOne]['Data']==float(-9999))&             # index of missing values
                                  (DateNum>=DateNum[iog[0]])&                          # that occur between the first
                                  (DateNum<=DateNum[iog[-1]]))[0]                      # and last dates used to define f
                # Now we step through the indices of the missing values and discard
                # contiguous blocks longer than maxlen.
                # !!! The following code is klunky and could be re-written to be
                # !!! neater and faster.
                # First, define 2 temporary arrays used and initialise 2 counters.
                tmp1 = numpy.zeros(len(iom),int)
                tmp2 = numpy.zeros(len(iom),int)
                k=0
                n=0
                # step through the array of idices for missing values
                for i in range(len(iom)-1):
                    dn = iom[i+1]-iom[i]        # change in index number from one element of iom to the next
                    if dn==1:                   # if the change is 1 then we are still in a contiguous block
                        tmp1[n] = iom[i]        # save the index into a temporary array
                        n = n + 1               # increment the contiguous block length counter
                    elif dn>1:                  # if the change is greater than 1 then we have come to the end of a contiguous block
                        if n<maxlen:            # if the contiguous block length is less then maxlen
                            tmp1[n]=iom[i]      # save the last index of the contiguous block
                            tmp2[k:k+n+1] = tmp1[0:n+1]   # concatenate the indices for this block to any previous block with length less than maxlen
                            k=k+n+1             # update the pointer to the concatenating array
                        n=0                     # reset the contiguous block length counter
                if k>0:                         # do the interpolation only if 1 gap is less than maxlen
                    tmp2[k] = iom[-1]               # just accept the last missing value index regardless
                    iom_new = tmp2[:k+1]            # the array of missing data indices with contiguous block lengths less than maxlen
                    ds.series[ThisOne]['Data'][iom_new] = f(DateNum[iom_new]).astype(numpy.float32)        # fill missing values with linear interpolations
                    ds.series[ThisOne]['Flag'][iom_new] = 60
        else:
            log.warn('  Interpolate over missing:  '+ThisOne+' not in dataset')

def MassmanStandard(cf,ds,Ta_in='Ta',Ah_in='Ah',ps_in='ps',ustar_in='ustar',ustar_out='ustar',L_in='L',L_out ='L',uw_out='uw',vw_out='vw',wT_out='wT',wA_out='wA',wC_out='wC',u_in='u',uw_in='uw',vw_in='vw',wT_in='wT',wC_in='wC',wA_in='wA'):
    """
       Massman corrections.
       The steps involved are as follows:
        1) calculate ustar and L using rotated but otherwise uncorrected covariances
       """
    if 'Massman' not in cf:
        log.info(' Massman section not found in control file, no corrections applied')
        return
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='MassmanVars'):
        MArgs = ast.literal_eval(cf['FunctionArgs']['MassmanVars'])
        Ta_in = MArgs[0]
        Ah_in = MArgs[1]
        ps_in = MArgs[2]
        ustar_in = MArgs[3]
        L_in = MArgs[4]
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='MassmanOuts'):
        MOut = ast.literal_eval(cf['FunctionArgs']['MassmanOuts'])
        ustar_out = MOut[0]
        L_out = MOut[1]
        uw_out = MOut[2]
        vw_out = MOut[3]
        wT_out = MOut[4]
        wA_out = MOut[5]
        wC_out = MOut[6]
    log.info(' Correcting for flux loss from spectral attenuation')
    zmd = float(cf['Massman']['zmd'])             # z-d for site
    angle = float(cf['Massman']['angle'])         # CSAT3-IRGA separation angle
    CSATarm = float(cf['Massman']['CSATarm'])     # CSAT3 mounting distance
    IRGAarm = float(cf['Massman']['IRGAarm'])     # IRGA mounting distance
    lLat = numpy.ma.sin(numpy.deg2rad(angle)) * IRGAarm
    lLong = CSATarm - (numpy.ma.cos(numpy.deg2rad(angle)) * IRGAarm)
    # *** Massman_1stpass starts here ***
    #  The code for the first and second passes is very similar.  It would be useful to make them the
    #  same and put into a loop to reduce the nu,ber of lines in this function.
    # calculate ustar and Monin-Obukhov length from rotated but otherwise uncorrected covariances
    Ta,f = qcutils.GetSeriesasMA(ds,Ta_in)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_in)
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    nRecs = numpy.size(Ta)
    u,f = qcutils.GetSeriesasMA(ds,u_in)
    uw,f = qcutils.GetSeriesasMA(ds,uw_in)
    vw,f = qcutils.GetSeriesasMA(ds,vw_in)
    wT,f = qcutils.GetSeriesasMA(ds,wT_in)
    wC,f = qcutils.GetSeriesasMA(ds,wC_in)
    wA,f = qcutils.GetSeriesasMA(ds,wA_in)
    if ustar_in not in ds.series.keys():
        ustarm = numpy.ma.sqrt(numpy.ma.sqrt(uw ** 2 + vw ** 2))
    else:
        ustarm,f = qcutils.GetSeriesasMA(ds,ustar_in)
    if L_in not in ds.series.keys():
        Lm = mf.molen(Ta, Ah, ps, ustarm, wT)
    else:
        Lm,f = qcutils.GetSeriesasMA(ds,Lm_in)
    # now calculate z on L
    zoLm = zmd / Lm
    # start calculating the correction coefficients for approximate corrections
    #  create nxMom, nxScalar and alpha series with their unstable values by default
    nxMom, nxScalar, alpha = qcutils.nxMom_nxScalar_alpha(zoLm)
    # now calculate the fxMom and fxScalar coefficients
    fxMom = nxMom * u / zmd
    fxScalar = nxScalar * u / zmd
    # compute spectral filters
    tao_eMom = ((c.lwVert / (5.7 * u)) ** 2) + ((c.lwHor / (2.8 * u)) ** 2)
    tao_ewT = ((c.lwVert / (8.4 * u)) ** 2) + ((c.lTv / (4.0 * u)) ** 2)
    tao_ewIRGA = ((c.lwVert / (8.4 * u)) ** 2) + ((c.lIRGA / (4.0 * u)) ** 2) \
                 + ((lLat / (1.1 * u)) ** 2) + ((lLong / (1.05 * u)) ** 2)
    tao_b = c.Tb / 2.8
    # calculate coefficients
    bMom = qcutils.bp(fxMom,tao_b)
    bScalar = qcutils.bp(fxScalar,tao_b)
    pMom = qcutils.bp(fxMom,tao_eMom)
    pwT = qcutils.bp(fxScalar,tao_ewT)
    # calculate corrections for momentum and scalars
    rMom = qcutils.r(bMom, pMom, alpha)        # I suspect that rMom and rwT are the same functions
    rwT = qcutils.r(bScalar, pwT, alpha)
    # determine approximately-true Massman fluxes
    uwm = uw / rMom
    vwm = vw / rMom
    wTm = wT / rwT
    # *** Massman_1stpass ends here ***
    # *** Massman_2ndpass starts here ***
    # we have calculated the first pass corrected momentum and temperature covariances, now we use
    # these to calculate the final corrections
    #  first, get the 2nd pass corrected friction velocity and Monin-Obukhov length
    ustarm = numpy.ma.sqrt(numpy.ma.sqrt(uwm ** 2 + vwm ** 2))
    Lm = mf.molen(Ta, Ah, ps, ustarm, wTm)
    zoLm = zmd / Lm
    nxMom, nxScalar, alpha = qcutils.nxMom_nxScalar_alpha(zoLm)
    fxMom = nxMom * (u / zmd)
    fxScalar = nxScalar * (u / zmd)
    # calculate coefficients
    bMom = qcutils.bp(fxMom,tao_b)
    bScalar = qcutils.bp(fxScalar,tao_b)
    pMom = qcutils.bp(fxMom,tao_eMom)
    pwT = qcutils.bp(fxScalar,tao_ewT)
    pwIRGA = qcutils.bp(fxScalar,tao_ewIRGA)
    # calculate corrections for momentum and scalars
    rMom = qcutils.r(bMom, pMom, alpha)
    rwT = qcutils.r(bScalar, pwT, alpha)
    rwIRGA = qcutils.r(bScalar, pwIRGA, alpha)
    # determine true fluxes
    uwM = uw / rMom
    vwM = vw / rMom
    wTM = wT / rwT
    wCM = wC / rwIRGA
    wAM = wA / rwIRGA
    ustarM = numpy.ma.sqrt(numpy.ma.sqrt(uwM ** 2 + vwM ** 2))
    LM = mf.molen(Ta, Ah, ps, ustarM, wTM)
    # write the 2nd pass Massman corrected covariances to the data structure
    qcutils.CreateSeries(ds,ustar_out,ustarM,FList=[Ta_in,Ah_in,ps_in,u_in,uw_in,vw_in,wT_in,wC_in,wA_in],Descr='Massman true ustar',Units='m/s')
    qcutils.CreateSeries(ds,L_out,LM,FList=[Ta_in,Ah_in,ps_in,u_in,uw_in,vw_in,wT_in,wC_in,wA_in],Descr='Massman true Obukhov Length',Units='m')
    qcutils.CreateSeries(ds,uw_out,uwM,FList=[Ta_in,Ah_in,ps_in,u_in,uw_in,vw_in,wT_in,wC_in,wA_in],Descr='Massman true Cov(uw)',Units='m2/s2')
    qcutils.CreateSeries(ds,vw_out,vwM,FList=[Ta_in,Ah_in,ps_in,u_in,uw_in,vw_in,wT_in,wC_in,wA_in],Descr='Massman true Cov(vw)',Units='m2/s2')
    qcutils.CreateSeries(ds,wT_out,wTM,FList=[Ta_in,Ah_in,ps_in,u_in,uw_in,vw_in,wT_in,wC_in,wA_in],Descr='Massman true Cov(wT)',Units='mC/s')
    qcutils.CreateSeries(ds,wA_out,wAM,FList=[Ta_in,Ah_in,ps_in,u_in,uw_in,vw_in,wT_in,wC_in,wA_in],Descr='Massman true Cov(wA)',Units='g/m2/s')
    qcutils.CreateSeries(ds,wC_out,wCM,FList=[Ta_in,Ah_in,ps_in,u_in,uw_in,vw_in,wT_in,wC_in,wA_in],Descr='Massman true Cov(wC)',Units='mg/m2/s')
    # *** Massman_2ndpass ends here ***
    
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='MassmanFlag') and cf['General']['MassmanFlag'] == 'True':
        keys = [ustar_out,L_out,uw_out,vw_out,wT_out,wA_out,wC_out]
        for ThisOne in keys:
            testseries,f = qcutils.GetSeriesasMA(ds,ThisOne)
            mask = numpy.ma.getmask(testseries)
            index = numpy.where(mask.astype(int)==1)
            ds.series[ThisOne]['Flag'][index] = 12
    else:
        keys = [ustar_out,L_out,uw_out,vw_out,wT_out,wA_out,wC_out]
        for ThisOne in keys:
            testseries,f = qcutils.GetSeriesasMA(ds,ThisOne)
            mask = numpy.ma.getmask(testseries)
            index = numpy.where((numpy.mod(f,10)==0) & (mask.astype(int)==1))    # find the elements with flag = 0, 10, 20 etc and masked (check for masked data with good data flag)
            ds.series[ThisOne]['Flag'][index] = 12

def MergeSeries(ds,Destination,Source,QCFlag_OK):
    """
        Merge two series of data to produce one series containing the best data from both.
        Calling syntax is: MergeSeries(ds,Destination,Source,QCFlag_OK)
         where ds is the data structure containing all series
               Destination (str) is the label of the destination series
               Source (list) is the label of the series to be merged in order
               QCFlag_OK (list) is a list of QC flag values for which the data is considered acceptable
        If the QC flag for Primary is in QCFlag_OK, the value from Primary is placed in destination.
        If the QC flag for Primary is not in QCFlag_OK but the QC flag for Secondary is, the value
        from Secondary is placed in Destination.
        """
    log.info(' Merging series '+str(Source)+' into '+Destination)
    nSeries = len(Source)
    if nSeries==0:
        log.error('  MergeSeries: no input series specified')
        return
    if nSeries==1:
        if Source[0] not in ds.series.keys():
            log.error('  MergeSeries: primary input series '+Source[0]+' not found')
            return
        data = ds.series[Source[0]]['Data'].copy()
        flag = ds.series[Source[0]]['Flag'].copy()
        SeriesNameString = Source[0]
        SeriesUnitString = ds.series[Source[0]]['Attr']['units']
    else:
        if Source[0] not in ds.series.keys():
            log.error('  MergeSeries: primary input series '+Source[0]+' not found')
            return
        data = ds.series[Source[0]]['Data'].copy()
        flag = ds.series[Source[0]]['Flag'].copy()
        SeriesNameString = Source[0]
        SeriesUnitString = ds.series[Source[0]]['Attr']['units']
        Source.remove(Source[0])
        for ThisOne in Source:
            if ThisOne in ds.series.keys():
                SeriesNameString = SeriesNameString+', '+ThisOne
                indx1 = numpy.zeros(numpy.size(data),dtype=numpy.int)
                indx2 = numpy.zeros(numpy.size(data),dtype=numpy.int)
                for okflag in QCFlag_OK:
                    index = numpy.where((flag==okflag))[0]                             # index of acceptable primary values
                    indx1[index] = 1                                                   # set primary index to 1 when primary good
                    index = numpy.where((ds.series[ThisOne]['Flag']==okflag))[0]       # same process for secondary
                    indx2[index] = 1
                index = numpy.where((indx1!=1)&(indx2==1))[0]           # index where primary bad but secondary good
                data[index] = ds.series[ThisOne]['Data'][index]         # replace bad primary with good secondary
                flag[index] = ds.series[ThisOne]['Flag'][index]
            else:
                log.error('  MergeSeries: secondary input series '+ThisOne+' not found')
    if Destination not in ds.series.keys():                 # create new series if destination does not exist
        qcutils.CreateSeries(ds,Destination,data,Flag=flag,Descr='Merged from '+SeriesNameString,Units=SeriesUnitString,Standard=ds.series[Source[0]]['Attr']['standard_name'])
    else:
        ds.series[Destination]['Data'] = data.copy()
        ds.series[Destination]['Flag'] = flag.copy()
        ds.series[Destination]['Attr']['long_name'] = 'Merged from '+SeriesNameString
        ds.series[Destination]['Attr']['units'] = SeriesUnitString

def prep_aerodynamicresistance(cf,ds,Cdmethod,Cemethod,Ce_2layer):
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='PMin'):
        PMin = ast.literal_eval(cf['PenmanMonteith']['PMin'])
    else:
        PMin = ['Fe', 'Ta', 'Ah', 'ps', 'Ws', 'Fn', 'Fsd', 'Fg', 'VPD']     # ***
    
    Level = ds.globalattributes['Level']
    log.info(' Computing Penman-Monteith bulk stomatal resistance at level '+Level)
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='PMcritFsd'):
        critFsd = float(cf['PenmanMonteith']['PMcritFsd'])
    else:
        critFsd = 10.
    
    if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='PMcritFe'):
        critFe = float(cf['PenmanMonteith']['PMcritFe'])
    else:
        critFe = 0.
    
    Fe,f = qcutils.GetSeriesasMA(ds,PMin[0])
    Fsd,f = qcutils.GetSeriesasMA(ds,PMin[6])
    Uavg,f = qcutils.GetSeriesasMA(ds,PMin[4])
    uindex = numpy.ma.where(Uavg == 0)[0]
    Feindex = numpy.ma.where(Fe < critFe)[0]
    Fsdindex = numpy.ma.where(Fsd < critFsd)[0]
    Uavg[uindex] = 0.000000000000001
    # use bulk transfer coefficient method
    if Cemethod == 'True':
        # rav parameterised with q profile measurements
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='profileq'):
            qList = ast.literal_eval(cf['PenmanMonteith']['profileq'])
        else:
            log.error('  PenmanMonteith:  profileq not given')
            return
        
        outList = ['Ce_1layer','rav_1layer','rE_1layer','GE_1layer']
        attribute = 'Ce with q profile, '
        log.info('  Ce method (Brutseart 1982, Stull 1988) used to estimate aerodynamic resistance, rav')
        log.info('   Ce method: qList: '+str(qList))
        Ce, rav, ravindex = get_rav(cf,ds,Uavg,PMin,qList)
        rst, rstindex, Gst, Gstindex = get_rstGst(cf,ds,PMin,rav)
        flagList = [PMin[0],PMin[1],PMin[2],PMin[3],PMin[4],PMin[5],PMin[6],PMin[7],qList[0],qList[1]]
        qcutils.CreateSeries(ds,outList[0],Ce,FList=flagList,Descr='Bulk transfer coefficient, '+attribute+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[1],rav,FList=flagList,Descr='Aerodynamic resistance, '+attribute+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[2],rst,FList=flagList,Descr='Stomatal resistance from Penman-Monteith inversion, '+attribute+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[3],Gst,FList=flagList,Descr='Conductance from Penman-Monteith inversion, '+attribute+Level,Units='mmolH2O/(m2ground s)')
        for listindex in range(0,4):
            ds.series[outList[listindex]]['Attr']['InputSeries'] = PMin
            ds.series[outList[listindex]]['Attr']['FsdCutoff'] = critFsd
            ds.series[outList[listindex]]['Attr']['FeCutoff'] = critFe
            ds.series[outList[listindex]]['Flag'][rstindex] = 131
            ds.series[outList[listindex]]['Flag'][ravindex] = 131
            ds.series[outList[listindex]]['Flag'][uindex] = 134
            ds.series[outList[listindex]]['Flag'][Feindex] = 132
            ds.series[outList[listindex]]['Flag'][Fsdindex] = 133
            ds.series[outList[listindex]]['Data'][rstindex] = numpy.float(-9999)
            ds.series[outList[listindex]]['Data'][ravindex] = numpy.float(-9999)
            ds.series[outList[listindex]]['Data'][uindex] = numpy.float(-9999)
            ds.series[outList[listindex]]['Data'][Feindex] = numpy.float(-9999)
            ds.series[outList[listindex]]['Data'][Fsdindex] = numpy.float(-9999)
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='rlvCe') and cf['PenmanMonteith']['rlvCe'] == 'True':
            rlv, flag = get_leafresistance(cf,ds,outList[2])
            qcutils.CreateSeries(ds,'rLE_1layer',rlv,Flag=0,Descr='leaf resistance from Penman-Monteith inversion, Ce-method, under well-illuminated (> 600 W m-2 Fsd) conditions',Units='s/m')
            ds.series['rLE_1layer']['Flag'] = flag
    
    # use 2-layer bulk transfer coefficient method
    if Ce_2layer == 'True':
        # rav parameterised with q profile measurements
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='base_profileq'):
            base_qList = ast.literal_eval(cf['PenmanMonteith']['base_profileq'])
        else:
            log.error('  PenmanMonteith:  base_profileq not given')
            return
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='top_profileq'):
            top_qList = ast.literal_eval(cf['PenmanMonteith']['top_profileq'])
        else:
            log.error('  PenmanMonteith:  top_profileq not given')
            return
        
        outList = ['Ce_base','rav_base','rE_base','GE_base','Ce_top','rav_top','rE_top','GE_top','Ce_full','rav_full','rE_full','GE_full','rE_2layer','GE_2layer','rav_2layer']
        attribute = 'Ce 2-layer with q profile, '
        log.info('  Ce method (Brutseart 1982, Stull 1988) used to estimate aerodynamic resistance, rav')
        log.info('   2-layer Ce method: lower layer qList: '+str(base_qList))
        log.info('   2-layer Ce method: upper layer qList: '+str(top_qList))
        log.info('   2-layer Ce method: full layer qList: '+str(top_qList[0])+', '+str(base_qList[1]))
        flagListTop = [PMin[0],PMin[1],PMin[2],PMin[3],PMin[4],PMin[5],PMin[6],PMin[7],top_qList[0],top_qList[1]]
        flagListBase = [PMin[0],PMin[1],PMin[2],PMin[3],PMin[4],PMin[5],PMin[6],PMin[7],base_qList[0],base_qList[1]]
        flagListFull = [PMin[0],PMin[1],PMin[2],PMin[3],PMin[4],PMin[5],PMin[6],PMin[7],top_qList[0],base_qList[1]]
        flagList = [PMin[0],PMin[1],PMin[2],PMin[3],PMin[4],PMin[5],PMin[6],PMin[7],base_qList[0],base_qList[1],top_qList[0],top_qList[1]]
        Ce_top, rav_top, ravindex_top = get_rav(cf,ds,Uavg,PMin,top_qList,layer='top_',method='Ce_2layer')
        Ce_base, rav_base, ravindex_base = get_rav(cf,ds,Uavg,PMin,base_qList,layer='base_',method='Ce_2layer')
        Ce_full, rav_full, ravindex_full = get_rav(cf,ds,Uavg,PMin,[top_qList[0],base_qList[1]],method='Ce_2layer')
        rav_diff1 = numpy.setdiff1d(ravindex_base,ravindex_top)
        rav_diff2 = numpy.setdiff1d(ravindex_top,ravindex_base)
        rav_diff3 = numpy.concatenate((rav_diff2,rav_diff1), axis=0)
        ravindex_neither = numpy.setdiff1d(ravindex_top,rav_diff3)
        
        #determine rav when rav = rav_base (rav_top <= 0)
        rav = (rav_full * rav_top) / (rav_full + rav_top)
        
        #determine rav when rav = rav_top (rav_base <= 0)
        rav[ravindex_base] = rav_top[ravindex_base]
        
        #determine rav when rav = rav_base (rav_top <= 0)
        rav[ravindex_top] = rav_base[ravindex_top]
        
        ravindex = numpy.where(rav < 0)[0]
        ravgoodindex_top = numpy.where(rav_top > 0)[0]
        ravgoodindex_base = numpy.where(rav_base > 0)[0]
        ravgoodindex_full = numpy.where(rav_full > 0)[0]
        ravgoodindex = numpy.where(rav > 0)[0]
        rst_top, rstindex_top, Gst_top, Gstindex_top = get_rstGst(cf,ds,PMin,rav_top)
        rst_base, rstindex_base, Gst_base, Gstindex_base = get_rstGst(cf,ds,PMin,rav_base)
        rst_full, rstindex_full, Gst_full, Gstindex_full = get_rstGst(cf,ds,PMin,rav_full)
        rst, rstindex, Gst, Gstindex = get_rstGst(cf,ds,PMin,rav)
        qcutils.CreateSeries(ds,outList[0],Ce_base,FList=flagListBase,Descr='Bulk transfer coefficient, '+attribute+'base layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[1],rav_base,FList=flagListBase,Descr='Aerodynamic resistance, '+attribute+'base layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[2],rst_base,FList=flagListBase,Descr='Stomatal resistance from Penman-Monteith inversion, '+attribute+'base layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[3],Gst_base,FList=flagListBase,Descr='Conductance from Penman-Monteith inversion, '+attribute+'base layer, '+Level,Units='mmolH2O/(m2ground s)')
        qcutils.CreateSeries(ds,outList[4],Ce_top,FList=flagListTop,Descr='Bulk transfer coefficient, '+attribute+'top layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[5],rav_top,FList=flagListTop,Descr='Aerodynamic resistance, '+attribute+'top layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[6],rst_top,FList=flagListTop,Descr='Stomatal resistance from Penman-Monteith inversion, '+attribute+'top layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[7],Gst_top,FList=flagListTop,Descr='Conductance from Penman-Monteith inversion, '+attribute+'top layer, '+Level,Units='mmolH2O/(m2ground s)')
        qcutils.CreateSeries(ds,outList[8],Ce_full,FList=flagListFull,Descr='Bulk transfer coefficient, '+attribute+'full layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[9],rav_full,FList=flagListFull,Descr='Aerodynamic resistance, '+attribute+'full layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[10],rst_full,FList=flagListFull,Descr='Stomatal resistance from Penman-Monteith inversion, '+attribute+'full layer, '+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[11],Gst_full,FList=flagListFull,Descr='Conductance from Penman-Monteith inversion, '+attribute+'full layer, '+Level,Units='mmolH2O/(m2ground s)')
        qcutils.CreateSeries(ds,outList[12],rst,FList=flagList,Descr='Stomatal resistance from Penman-Monteith inversion, '+attribute+Level,Units='s/m')
        qcutils.CreateSeries(ds,outList[13],Gst,FList=flagList,Descr='Conductance from Penman-Monteith inversion, '+attribute+Level,Units='mmolH2O/(m2ground s)')
        qcutils.CreateSeries(ds,outList[14],rav,FList=flagList,Descr='Aerodynamic resistance, '+attribute+Level,Units='s/m')
        for listindex in range(0,15):
            ds.series[outList[listindex]]['Attr']['InputSeries'] = PMin
            ds.series[outList[listindex]]['Attr']['FsdCutoff'] = critFsd
            ds.series[outList[listindex]]['Attr']['FeCutoff'] = critFe
            goodflagindex = numpy.where(numpy.mod(ds.series[outList[listindex]]['Flag'],10)==0)[0]
            badflagindex = numpy.where(numpy.mod(ds.series[outList[listindex]]['Flag'],10)!=0)[0]
            if '_base' in outList[listindex]:
                goodflagonlyindex = numpy.setdiff1d(ravindex_top,goodflagindex)
                goodravonlyindex = numpy.setdiff1d(goodflagindex,ravindex_top)
                goodnotbothindex = numpy.concatenate((goodflagonlyindex,goodravonlyindex), axis=0)
                goodbothindex = numpy.setdiff1d(ravindex_top,goodnotbothindex)
                ds.series[outList[listindex]]['Flag'][goodbothindex] = 150
                ds.series[outList[listindex]]['Flag'][rstindex_base] = 131
                ds.series[outList[listindex]]['Flag'][ravindex_base] = 131
                goodflagonlyindex = numpy.setdiff1d(ravgoodindex_top,goodflagindex)
                badravonlyindex = numpy.setdiff1d(goodflagindex,ravgoodindex_top)
                badnotbothindex = numpy.concatenate((goodflagonlyindex,badravonlyindex), axis=0)
                badbothindex = numpy.setdiff1d(ravgoodindex_top,badnotbothindex)
                ds.series[outList[listindex]]['Flag'][badbothindex] = 151
                ds.series[outList[listindex]]['Data'][rstindex_base] = numpy.float(-9999)
                ds.series[outList[listindex]]['Data'][ravindex_base] = numpy.float(-9999)
                ds.series[outList[listindex]]['Data'][ravgoodindex_top] = numpy.float(-9999)
            if '_top' in outList[listindex]:
                goodflagonlyindex140 = numpy.setdiff1d(ravindex_base,goodflagindex)
                goodflagonlyindex160 = numpy.setdiff1d(ravgoodindex_base,goodflagindex)
                goodravonlyindex140 = numpy.setdiff1d(goodflagindex,ravindex_base)
                goodravonlyindex160 = numpy.setdiff1d(goodflagindex,ravgoodindex_base)
                goodnotbothindex140 = numpy.concatenate((goodflagonlyindex140,goodravonlyindex140), axis=0)
                goodnotbothindex160 = numpy.concatenate((goodflagonlyindex160,goodravonlyindex160), axis=0)
                goodbothindex140 = numpy.setdiff1d(ravindex_base,goodnotbothindex140)
                goodbothindex160 = numpy.setdiff1d(ravgoodindex_base,goodnotbothindex160)
                ds.series[outList[listindex]]['Flag'][goodbothindex140] = 140
                ds.series[outList[listindex]]['Flag'][goodbothindex160] = 160
                ds.series[outList[listindex]]['Flag'][rstindex_top] = 131
                ds.series[outList[listindex]]['Flag'][ravindex_top] = 131
                ds.series[outList[listindex]]['Data'][rstindex_top] = numpy.float(-9999)
                ds.series[outList[listindex]]['Data'][ravindex_top] = numpy.float(-9999)
            if '_full' in outList[listindex]:
                goodflagonlyindex = numpy.setdiff1d(ravgoodindex_full,goodflagindex)
                goodravonlyindex = numpy.setdiff1d(goodflagindex,ravgoodindex_full)
                goodnotbothindex = numpy.concatenate((goodflagonlyindex,goodravonlyindex), axis=0)
                goodbothindex = numpy.setdiff1d(ravgoodindex_full,goodnotbothindex)
                ds.series[outList[listindex]]['Flag'][goodbothindex] = 160
                ds.series[outList[listindex]]['Flag'][rstindex_full] = 131
                ds.series[outList[listindex]]['Flag'][ravindex_full] = 131
                goodflagonlyindex_top = numpy.setdiff1d(ravindex_top,goodflagindex)
                goodflagonlyindex_base = numpy.setdiff1d(ravindex_base,goodflagindex)
                badravonlyindex_top = numpy.setdiff1d(goodflagindex,ravindex_top)
                badravonlyindex_base = numpy.setdiff1d(goodflagindex,ravindex_base)
                badnotbothindex_top = numpy.concatenate((goodflagonlyindex_top,badravonlyindex_top), axis=0)
                badnotbothindex_base = numpy.concatenate((goodflagonlyindex_base,badravonlyindex_base), axis=0)
                badbothindex_top = numpy.setdiff1d(ravindex_top,badnotbothindex_top)
                badbothindex_base = numpy.setdiff1d(ravindex_base,badnotbothindex_base)
                ds.series[outList[listindex]]['Flag'][badbothindex_top] = 161
                ds.series[outList[listindex]]['Flag'][badbothindex_base] = 161
                ds.series[outList[listindex]]['Data'][rstindex_full] = numpy.float(-9999)
                ds.series[outList[listindex]]['Data'][ravindex_full] = numpy.float(-9999)
                ds.series[outList[listindex]]['Data'][ravindex_top] = numpy.float(-9999)
                ds.series[outList[listindex]]['Data'][ravindex_base] = numpy.float(-9999)
            if '_2layer' in outList[listindex]:
                goodflagonlyindex140 = numpy.setdiff1d(ravindex_base,goodflagindex)
                goodflagonlyindex150 = numpy.setdiff1d(ravindex_top,goodflagindex)
                goodflagonlyindex160 = numpy.setdiff1d(ravgoodindex_full,goodflagindex)
                goodravonlyindex140 = numpy.setdiff1d(goodflagindex,ravindex_base)
                goodravonlyindex150 = numpy.setdiff1d(goodflagindex,ravindex_top)
                goodravonlyindex160 = numpy.setdiff1d(goodflagindex,ravgoodindex_full)
                goodnotbothindex140 = numpy.concatenate((goodflagonlyindex140,goodravonlyindex140), axis=0)
                goodnotbothindex150 = numpy.concatenate((goodflagonlyindex150,goodravonlyindex150), axis=0)
                goodnotbothindex160 = numpy.concatenate((goodflagonlyindex160,goodravonlyindex160), axis=0)
                goodbothindex140 = numpy.setdiff1d(ravindex_base,goodnotbothindex140)
                goodbothindex150 = numpy.setdiff1d(ravindex_top,goodnotbothindex150)
                goodbothindex160 = numpy.setdiff1d(ravgoodindex_full,goodnotbothindex160)
                ds.series[outList[listindex]]['Flag'][goodbothindex160] = 160
                ds.series[outList[listindex]]['Flag'][goodbothindex140] = 140
                ds.series[outList[listindex]]['Flag'][goodbothindex150] = 150
                ds.series[outList[listindex]]['Flag'][rstindex] = 131
                ds.series[outList[listindex]]['Flag'][ravindex] = 131
                ds.series[outList[listindex]]['Data'][rstindex] = numpy.float(-9999)
                ds.series[outList[listindex]]['Data'][ravindex] = numpy.float(-9999)
            
            ds.series[outList[listindex]]['Flag'][uindex] = 134
            ds.series[outList[listindex]]['Flag'][Feindex] = 132
            ds.series[outList[listindex]]['Flag'][Fsdindex] = 133
            ds.series[outList[listindex]]['Data'][badflagindex] = numpy.float(-9999)
            ds.series[outList[listindex]]['Data'][uindex] = numpy.float(-9999)
            ds.series[outList[listindex]]['Data'][Feindex] = numpy.float(-9999)
            ds.series[outList[listindex]]['Data'][Fsdindex] = numpy.float(-9999)
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='rlv2layer') and cf['PenmanMonteith']['rlv2layer'] == 'True':
            rlv, flag = get_leafresistance(cf,ds,outList[12])
            qcutils.CreateSeries(ds,'rLE_2layer',rlv,Flag=0,Descr='leaf resistance from Penman-Monteith inversion, 2layer Ce-method, under well-illuminated (> 600 W m-2 Fsd) conditions',Units='s/m')
            ds.series['rLE_2layer']['Flag'] = flag
    
    # use drag coefficient method
    if Cdmethod == 'True':
        log.info('  Cd method (Jensen 1990, Luening 2008) used to estimate aerodynamic resistance, ra')
        get_canopyresistance(cf,ds,Uavg,uindex,PMin,Level,critFsd,critFe)
        
        if qcutils.cfkeycheck(cf,Base='PenmanMonteith',ThisOne='rlm') and cf['PenmanMonteith']['rlm'] == 'True':
            rlm, flag = get_leafresistance(cf,ds,'rC')
            qcutils.CreateSeries(ds,'rLC',rlm,Flag=0,Descr='leaf resistance from Penman-Monteith inversion, Cd-method, under well-illuminated (> 600 W m-2 Fsd) conditions',Units='s/m')
            ds.series['rLC']['Flag'] = flag
    
    return

def PT100(ds,T_out,R_in,m):
    log.info(' Calculating temperature from PT100 resistance')
    R,f = qcutils.GetSeriesasMA(ds,R_in)
    R = m*R
    T = (-c.PT100_alpha+numpy.sqrt(c.PT100_alpha**2-4*c.PT100_beta*(-R/100+1)))/(2*c.PT100_beta)
    qcutils.CreateSeries(ds,T_out,T,FList=[R_in],
                         Descr='Calculated PT100 temperature using '+str(R_in),Units='degC')

def ReplaceOnDiff(cf,ds,series=''):
    # Gap fill using data from alternate sites specified in the control file
    ts = ds.globalattributes['time_step']
    if len(series)!=0:
        ds_alt = {}                     # create a dictionary for the data from alternate sites
        open_ncfiles = []               # create an empty list of open netCDF files
        for ThisOne in series:          # loop over variables in the series list
            # has ReplaceOnDiff been specified for this series?
            if qcutils.incf(cf,ThisOne) and qcutils.haskey(cf,ThisOne,'ReplaceOnDiff'):
                # loop over all entries in the ReplaceOnDiff section
                for Alt in cf['Variables'][ThisOne]['ReplaceOnDiff'].keys():
                    if 'FileName' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                        alt_filename = cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['FileName']
                        if 'AltVarName' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            alt_varname = cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['AltVarName']
                        else:
                            alt_varname = ThisOne
                        if alt_filename not in open_ncfiles:
                            n = len(open_ncfiles)
                            open_ncfiles.append(alt_filename)
                            ds_alt[n] = qcio.nc_read_series_file(alt_filename)
                        else:
                            n = open_ncfiles.index(alt_filename)
                        if 'Transform' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            AltDateTime = ds_alt[n].series['DateTime']['Data']
                            AltSeriesData = ds_alt[n].series[alt_varname]['Data']
                            TList = ast.literal_eval(cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['Transform'])
                            for TListEntry in TList:
                                qcts.TransformAlternate(TListEntry,AltDateTime,AltSeriesData,ts=ts)
                        if 'Range' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            RList = ast.literal_eval(cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['Range'])
                            for RListEntry in RList:
                                qcts.ReplaceWhenDiffExceedsRange(ds.series['DateTime']['Data'],ds.series[ThisOne],
                                                                 ds.series[ThisOne],ds_alt[n].series[alt_varname],
                                                                 RListEntry)
                    elif 'AltVarName' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                        alt_varname = ThisOne
                        if 'Range' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            RList = ast.literal_eval(cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['Range'])
                            for RListEntry in RList:
                                qcts.ReplaceWhenDiffExceedsRange(ds.series['DateTime']['Data'],ds.series[ThisOne],
                                                                 ds.series[ThisOne],ds.series[alt_varname],
                                                                 RListEntry)
                    else:
                        log.error('ReplaceOnDiff: Neither AltFileName nor AltVarName given in control file')
    else:
        log.error('ReplaceOnDiff: No input series specified')

def ReplaceWhereMissing(Destination,Primary,Secondary,FlagOffset=0):
    #print time.strftime('%X')+' Merging series '+Primary+' and '+Secondary+' into '+Destination
    p_data = Primary['Data'].copy()
    p_flag = Primary['Flag'].copy()
    s_data = Secondary['Data'].copy()
    s_flag = Secondary['Flag'].copy()
    if numpy.size(p_data)>numpy.size(s_data):
        p_data = p_data[0:numpy.size(s_data)]
    if numpy.size(s_data)>numpy.size(p_data):
        s_data = s_data[0:numpy.size(p_data)]
    index = numpy.where((abs(p_data-float(-9999))<c.eps)&
                        (abs(s_data-float(-9999))>c.eps))[0]
    p_data[index] = s_data[index]
    p_flag[index] = s_flag[index] + FlagOffset
    Destination['Data'] = Primary['Data'].copy()
    Destination['Flag'] = Primary['Flag'].copy()
    Destination['Data'][0:len(p_data)] = p_data
    Destination['Flag'][0:len(p_flag)] = p_flag
    Destination['Attr']['long_name'] = 'Merged from original and alternate'
    Destination['Attr']['units'] = Primary['Attr']['units']

def ReplaceWhenDiffExceedsRange(DateTime,Destination,Primary,Secondary,RList):
    #print time.strftime('%X')+' Replacing '+Primary+' with '+Secondary+' when difference exceeds threshold'
    # get the primary data series
    p_data = numpy.ma.array(Primary['Data'])
    p_flag = Primary['Flag'].copy()
    # get the secondary data series
    s_data = numpy.ma.array(Secondary['Data'])
    s_flag = Secondary['Flag'].copy()
    # truncate the longest series if the sizes do not match
    if numpy.size(p_data)!=numpy.size(s_data):
        log.warning(' ReplaceWhenDiffExceedsRange: Series lengths differ, longest will be truncated')
        if numpy.size(p_data)>numpy.size(s_data):
            p_data = p_data[0:numpy.size(s_data)]
        if numpy.size(s_data)>numpy.size(p_data):
            s_data = s_data[0:numpy.size(p_data)]
    # get the difference between the two data series
    d_data = p_data-s_data
    # normalise the difference if requested
    if RList[3]=='s':
        d_data = (p_data-s_data)/s_data
    elif RList[3]=='p':
        d_data = (p_data-s_data)/p_data
    #si = qcutils.GetDateIndex(DateTime,RList[0],0)
    #ei = qcutils.GetDateIndex(DateTime,RList[1],0)
    Range = RList[2]
    Upper = float(Range[0])
    Lower = float(Range[1])
    index = numpy.ma.where((abs(d_data)<Lower)|(abs(d_data)>Upper))
    p_data[index] = s_data[index]
    p_flag[index] = 70
    Destination['Data'] = numpy.ma.filled(p_data,float(-9999))
    Destination['Flag'] = p_flag.copy()
    Destination['Attr']['long_name'] = 'Replaced original with alternate when difference exceeded threshold'
    Destination['Attr']['units'] = Primary['Attr']['units']

def savitzky_golay(y, window_size, order, deriv=0):
    ''' Apply Savitsky-Golay low-pass filter to data.'''
    try:
        window_size = numpy.abs(numpy.int(window_size))
        order = numpy.abs(numpy.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = numpy.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = numpy.linalg.pinv(b).A[deriv]
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - numpy.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + numpy.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = numpy.concatenate((firstvals, y, lastvals))
    return numpy.convolve( m, y, mode='valid')

def Square(Series):
    tmp = numpy.array([-9999]*numpy.size(Series),Series.dtype)
    index = numpy.where(Series!=float(-9999))[0]
    tmp[index] = Series[index] ** 2
    return tmp

def SquareRoot(Series):
    tmp = numpy.array([-9999]*numpy.size(Series),Series.dtype)
    index = numpy.where(Series!=float(-9999))[0]
    tmp[index] = Series[index] ** .5
    return tmp

def TaFromTv(cf,ds,Ta_out='Ta_CSAT',Tv_in='Tv_CSAT',Ah_in='Ah',ps_in='ps'):
    # Calculate the air temperature from the virtual temperature, the
    # absolute humidity and the pressure.
    # NOTE: the virtual temperature is used in place of the air temperature
    #       to calculate the vapour pressure from the absolute humidity, the
    #       approximation involved here is of the order of 1%.
    log.info(' Calculating Ta from Tv')
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='Ta2Tv'):
        args = ast.literal_eval(cf['FunctionArgs']['Ta2Tv'])
        Ta_out = args[0]
        Tv_in = args[1]
        Ah_in = args[2]
        ps_in = args[3]
        
    Tv,f = qcutils.GetSeriesasMA(ds,Tv_in)
    Ah,f = qcutils.GetSeriesasMA(ds,Ah_in)
    ps,f = qcutils.GetSeriesasMA(ds,ps_in)
    nRecs = numpy.size(Tv)
    Ta_flag = numpy.zeros(nRecs,int)
    vp = mf.vapourpressure(Ah,Tv)
    mr = mf.mixingratio(ps,vp)
    q = mf.specifichumidity(mr)
    Ta_data = mf.tafromtv(Tv,q)
    mask = numpy.ma.getmask(Ta_data)
    index = numpy.where(mask.astype(int)==1)
    Ta_flag[index] = 15
    qcutils.CreateSeries(ds,Ta_out,Ta_data,Flag=Ta_flag,
                         Descr='Ta calculated from Tv using '+Tv_in,Units='degC',Standard='air_temperature')
    
def TransformAlternate(TList,DateTime,Series,ts=30):
    # Apply polynomial transform to data series being used as replacement data for gap filling
    #print time.strftime('%X')+' Applying polynomial transform to '+ThisOne
    si = qcutils.GetDateIndex(DateTime,TList[0],ts=ts,default=0,match='exact')
    ei = qcutils.GetDateIndex(DateTime,TList[1],ts=ts,default=-1,match='exact')
    Series = numpy.ma.masked_where(abs(Series-float(-9999))<c.eps,Series)
    Series[si:ei] = qcutils.polyval(TList[2],Series[si:ei])
    Series = numpy.ma.filled(Series,float(-9999))

def UstarFromFh(cf,ds,us_out='uscalc',T_in='Ta', Ah_in='Ah', p_in='ps', Fh_in='Fh', u_in='Ws_CSAT', us_in='ustar'):
    # Calculate ustar from sensible heat flux, wind speed and
    # roughness length using Wegstein's iterative method.
    #  T is the air temperature, C
    #  p is the atmospheric pressure, kPa
    #  H is the sensible heat flux, W/m^2
    #  u is the wind speed, m/s
    #  z is the measurement height minus the displacement height, m
    #  z0 is the momentum roughness length, m
    log.info(' Calculating ustar from (Fh,Ta,Ah,p,u)')
    # get z-d (measurement height minus displacement height) and z0 from the control file
    if qcutils.cfkeycheck(cf,Base='Params',ThisOne='zmd') and qcutils.cfkeycheck(cf,Base='Params',ThisOne='z0'):
        zmd = float(cf['Params']['zmd'])   # z-d for site
        z0 = float(cf['Params']['z0'])     # z0 for site
    else:
        log.error('Parameters zmd or z0 not found in control file.  u* not determined from Fh')
        return
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='ustarFh'):
        args = ast.literal_eval(cf['FunctionArgs']['ustarFh'])
        us_out = args[0]
        T_in = args[1]
        Ah_in = args[2]
        p_in = args[3]
        Fh_in = args[4]
        u_in = args[5]
        us_in = args[6]
    T,T_flag = qcutils.GetSeries(ds,T_in)
    Ah,Ah_flag = qcutils.GetSeries(ds,Ah_in)
    p,p_flag = qcutils.GetSeries(ds,p_in)
    Fh,Fh_flag = qcutils.GetSeries(ds,Fh_in)
    u,u_flag = qcutils.GetSeries(ds,u_in)
    nRecs = numpy.size(Fh)
    us = numpy.zeros(nRecs,dtype=numpy.float64) + numpy.float64(-9999)
    us_flag = numpy.zeros(nRecs,dtype=numpy.int)
    for i in range(nRecs):
        if((abs(T[i]-float(-9999))>c.eps)&(abs(Ah[i]-float(-9999))>c.eps)&
           (abs(p[i]-float(-9999))>c.eps)&(abs(Fh[i]-float(-9999))>c.eps)&
           (abs(u[i]-float(-9999))>c.eps)):
            #print ds.series['DateTime']['Data'][i],T[i]
            us[i] = qcutils.Wegstein(T[i], Ah[i], p[i], Fh[i], u[i], z, z0)
            us_flag[i] = 80
        else:
            us[i] = numpy.float64(-9999)
            us_flag[i] = 81
    qcutils.CreateSeries(ds,us_out,us,Flag=us_flag,Descr='ustar from (Fh,Ta,Ah,p,u)',Units='m/s')
    return us_in, us_out

def write_sums(cf,ds,ThisOne,xlCol,xlSheet,DoSum='False',DoMinMax='False',DoMean='False',DoSubSum='False',DoSoil='False'):
    monthabr = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    if qcutils.cfkeycheck(cf,Base='Params',ThisOne='firstMonth'):
        M1st = int(cf['Params']['firstMonth'])
    else:
        M1st = 1
    if qcutils.cfkeycheck(cf,Base='Params',ThisOne='secondMonth'):
        M2nd = int(cf['Params']['secondMonth'])
    else:
        M2nd = 12
    log.info(' Doing daily sums for '+ThisOne)
    Units = ds.series[ThisOne]['Attr']['units']
    
    xlRow = 1
    if xlCol == 0:
        xlSheet.write(xlRow,xlCol,'Month')
        xlCol = xlCol + 1
        xlSheet.write(xlRow,xlCol,'Day')
        xlCol = xlCol + 1
    xlSheet.write(xlRow,xlCol,'n')
    xlCol = xlCol + 1
    if DoMinMax == 'True':
        xlSheet.write(xlRow,xlCol,ThisOne+'_min')
        xlSheet.write(xlRow-1,xlCol,Units)
        xlCol = xlCol + 1
        xlSheet.write(xlRow,xlCol,ThisOne+'_max')
        if DoMean == 'True':
            xlSheet.write(xlRow-1,xlCol,Units)
            xlCol = xlCol + 1
            xlSheet.write(xlRow,xlCol,ThisOne+'_mean')
    elif DoMinMax == 'False' and DoMean == 'True':
        xlSheet.write(xlRow,xlCol,ThisOne+'_mean')
    elif DoMinMax == 'False' and DoMean == 'False':
        xlSheet.write(xlRow,xlCol,ThisOne)
        
    xlSheet.write(xlRow-1,xlCol,Units)

    if DoSubSum == 'True':
        xlCol = xlCol + 1
        xlSheet.write(xlRow,xlCol,'Pos n')
        xlCol = xlCol + 1
        xlSheet.write(xlRow,xlCol,ThisOne+'_pos')
        xlSheet.write(xlRow-1,xlCol,Units)
        xlCol = xlCol + 1
        xlSheet.write(xlRow,xlCol,'Neg n')
        xlCol = xlCol + 1
        xlSheet.write(xlRow,xlCol,ThisOne+'_neg')
        xlSheet.write(xlRow-1,xlCol,Units)
    
    data = numpy.ma.masked_where(abs(ds.series[ThisOne]['Data']-float(-9999))<c.eps,ds.series[ThisOne]['Data'])
    for month in range(M1st,M2nd+1):
        if month == 1 or month == 3 or month == 5 or month == 7 or month == 8 or month == 10 or month == 12:
            dRan = 31
        if month == 2:
            if ds.series['Year']['Data'][0] % 4 == 0:
                dRan = 29
            else:
                dRan = 28
        if month == 4 or month == 6 or month == 9 or month == 11:
            dRan = 30
            
        for day in range(1,dRan+1):
            xlRow = xlRow + 1
            PMList = ['GE_1layer_mol', 'GE_2layer_mol', 'GE_top_mol', 'GE_base_mol', 'GE_full_mol', 'GC_mol', 'rav_1layer', 'rE_1layer', 'rLE_1layer', 'GE_1layer', 'rav_2layer', 'rE_2layer', 'rLE_2layer', 'GE_2layer', 'rav_base', 'rE_base', 'GE_base', 'rav_top', 'rE_top', 'GE_top', 'rav_full', 'rE_full', 'GE_full', 'ram', 'rC', 'rLC', 'GC']
            CList = ['Re_mmol','Re_LRF_mmol','Re_n_mmol','Re_NEEmax_mmol','GPP','GPP_mmol','C_ppm']
            VarList = PMList + CList
            if ThisOne in VarList:
                di = numpy.where((ds.series['Month']['Data']==month) & (ds.series['Day']['Data']==day) & (numpy.mod(ds.series[ThisOne]['Flag'],10) == 0))[0]
                ti = numpy.where((ds.series['Month']['Data']==month) & (ds.series['Day']['Data']==day))[0]
                nRecs = len(ti)
                check = numpy.ma.empty(nRecs,str)
                for i in range(nRecs):
                    index = ti[i]
                    check[i] = ds.series['Day']['Data'][index]
                if len(check) < 48:
                    di = []
            else:
                di = numpy.where((ds.series['Month']['Data']==month) & (ds.series['Day']['Data']==day))[0]
                nRecs = len(di)
                check = numpy.ma.empty(nRecs,str)
                for i in range(nRecs):
                    index = di[i]
                    check[i] = ds.series['Day']['Data'][index]
                if len(check) < 48:
                    di = []
            
            if DoSoil == 'True':
                Num,Av = get_soilaverages(data[di])
                if xlCol == 3:
                    xlCol = 2
                    xlSheet.write(xlRow,xlCol-2,monthabr[month-1])
                    xlSheet.write(xlRow,xlCol-1,day)
                else:
                    xlCol = xlCol - 1
            else:
                if DoSum == 'True':
                    Num,Sum = get_sums(data[di])
                if DoMinMax == 'True':
                    Num,Min,Max = get_minmax(data[di])
                if DoMean == 'True':
                    if DoMinMax == 'True':
                        Num2,Av = get_averages(data[di])
                    else:
                        Num,Av = get_averages(data[di])
                if DoSubSum == 'True':
                    PosNum,NegNum,SumPos,SumNeg = get_subsums(data[di])
                xlCol = 2
                xlSheet.write(xlRow,xlCol-2,monthabr[month-1])
                xlSheet.write(xlRow,xlCol-1,day)
            
            xlSheet.write(xlRow,xlCol,Num)
            xlCol = xlCol + 1
            if DoSoil == 'True':
                xlSheet.write(xlRow,xlCol,Av)
            elif DoMinMax == 'True':
                xlSheet.write(xlRow,xlCol,Min)
                xlCol = xlCol + 1
                xlSheet.write(xlRow,xlCol,Max)
                if DoMean == 'True':
                    xlCol = xlCol + 1
                    xlSheet.write(xlRow,xlCol,Av)
            elif DoMinMax == 'False' and DoMean == 'True':
                xlSheet.write(xlRow,xlCol,Av)
            elif DoSum == 'True':
                xlSheet.write(xlRow,xlCol,Sum)
                if DoSubSum == 'True':
                    xlCol = xlCol + 1
                    xlSheet.write(xlRow,xlCol,PosNum)
                    xlCol = xlCol + 1
                    xlSheet.write(xlRow,xlCol,SumPos)
                    xlCol = xlCol + 1
                    xlSheet.write(xlRow,xlCol,NegNum)
                    xlCol = xlCol + 1
                    xlSheet.write(xlRow,xlCol,SumNeg)
    
    if DoSoil == 'True': 
        return xlCol,xlSheet
    else:
        return
