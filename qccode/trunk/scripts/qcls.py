"""
    OzFlux QC v1.6 24 Feb 2012;

    Version History:
    <<v1.0: 21 July 2011, code diversion reconciliation, PIsaac & JCleverly>>
    <<v1.0b 25 July 2011, with log capability, JCleverly>>
    <<v1.1b 26 July 2011, FhvtoFh output generalised and added to all sites qcl3, qcts functions modified to accept met constants or variables, JCleverly>>
    <<v1.2 23 Aug 2011, daily_sums functions moved to qcts module, JCleverly>>
    <<v1.3 26 Sep 2011, intermediate editing at OzFlux Black Mountain data workshop, PIsaac & JCleverly>>
    <<v1.4 30 Sep 2011, final version arrising from OzFlux Black Mountain data workshop, PIsaac & JCleverly>>
    <<v1.5 30 Nov 2011, revised l4qc calls in qc.py & Wombat modifications integrated, JCleverly>>
    <<v1.5.1 21 Feb 2012, code rationalisation and generalisation in progress, PIsaac & JCleverly>>
    <<v1.5.2 24 Feb 2012, de-bugging completion for ASM, PIsaac & JCleverly>>
    <<v1.6 24 Feb 2012, generalised qcls.l3qc, ASM tested ok L1-L4>>
"""

import sys
import logging
import ast
import constants as c
import copy
import numpy
import qcck
import qcio
import qcts
import qcutils
import time
import xlrd
import meteorologicalfunctions as mf

log = logging.getLogger('qc.ls')

def l2qc(cf,ds1):
    """
        Perform initial QA/QC on flux data
        Generates L2 from L1 data
        * check parameters specified in control file
        
        Functions performed:
            qcck.do_rangecheck*
            qcck.do_CSATcheck
            qcck.do_7500check
            qcck.do_diurnalcheck*
            qcck.do_excludedates*
            qcck.do_excludehours*
            qcts.albedo
        """
    # make a copy of the L1 data
    ds2 = copy.deepcopy(ds1)
    ds2.globalattributes['Level'] = 'L2'
    ds2.globalattributes['EPDversion'] = sys.version
    ds2.globalattributes['QCVersion'] = __doc__
    ds2.globalattributes['Functions'] = 'RangeCheck, CSATcheck, 7500check, diurnalcheck, excludedates, excludehours, albedo'
    # do the range check
    for ThisOne in ds2.series.keys():
        qcck.do_rangecheck(cf,ds2,ThisOne)
    log.info(' Finished the L2 range check')
    # do the diurnal check
    for ThisOne in ds2.series.keys():
        qcck.do_diurnalcheck(cf,ds2,ThisOne)
    log.info(' Finished the L2 diurnal average check')
    # exclude user specified date ranges
    for ThisOne in ds2.series.keys():
        qcck.do_excludedates(cf,ds2,ThisOne)
    log.info(' Finished the L2 exclude dates')
    # exclude user specified hour ranges
    for ThisOne in ds2.series.keys():
        qcck.do_excludehours(cf,ds2,ThisOne)
    log.info(' Finished the L2 exclude hours')
    # do the CSAT diagnostic check
    qcck.do_CSATcheck(cf,ds2)
    # do the LI-7500 diagnostic check
    qcck.do_7500check(cf,ds2)
    # constrain albedo estimates to full sun angles
    qcts.albedo(ds2)
    log.info(' Finished the albedo constraints')
    # apply linear corrections to the data
    qcck.do_linear(cf,ds2)
    # write series statistics to file
    qcutils.GetSeriesStats(cf,ds2)
    return ds2

def l3qc(cf,ds2):
    """
        Corrections
        Generates L3 from L2 data
        
        Functions performed:
            qcts.AddMetVars (optional)
            qcts.CorrectSWC (optional*)
            qcck.do_linear (all sites)
            qcutils.GetMergeList + qcts.MergeSeries Ah_EC (optional)x
            qcts.TaFromTv (optional)
            qcutils.GetMergeList + qcts.MergeSeries Ta_EC (optional)x
            qcts.CoordRotation2D (all sites)
            qcts.MassmanApprox (optional*)y
            qcts.Massman (optional*)y
            qcts.CalculateFluxes (used if Massman not optioned)x
            qcts.CalculateFluxesRM (used if Massman optioned)y
            qcts.FhvtoFh (all sites)
            qcts.Fe_WPL (WPL computed on fluxes, as with Campbell algorithm)+x
            qcts.Fc_WPL (WPL computed on fluxes, as with Campbell algorithm)+x
            qcts.Fe_WPLcov (WPL computed on kinematic fluxes (ie, covariances), as with WPL80)+y
            qcts.Fc_WPLcov (WPL computed on kinematic fluxes (ie, covariances), as with WPL80)+y
            qcts.CalculateNetRadiation (optional)
            qcutils.GetMergeList + qcts.MergeSeries Fsd (optional)
            qcutils.GetMergeList + qcts.MergeSeries Fn (optional*)
            qcts.InterpolateOverMissing (optional)
            AverageSeriesByElements (optional)
            qcts.CorrectFgForStorage (all sites)
            qcts.Average3SeriesByElements (optional)
            qcts.CalculateAvailableEnergy (optional)
            qcck.do_qcchecks (all sites)
            qcck.gaps (optional)
            
            *:  requires ancillary measurements for paratmerisation
            +:  each site requires one pair, either Fe_WPL & Fc_WPL (default) or Fe_WPLCov & FcWPLCov
            x:  required together in option set
            y:  required together in option set
        """
    # make a copy of the L2 data
    ds3 = copy.deepcopy(ds2)
    ds3.globalattributes['Level'] = 'L3'
    ds3.globalattributes['EPDversion'] = sys.version
    ds3.globalattributes['QCVersion'] = __doc__
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList'):
        l3functions = ast.literal_eval(cf['General']['FunctionList'])
    else:
        l3functions = ['do_linear', 'MergeSeriesAh', 'TaFromTv', 'MergeSeriesTa', 'CoordRotation2D', 'CalculateFluxes', 'FhvtoFh', 'Fe_WPL', 'Fc_WPL', 'MergeSeriesFsd', 'CalculateNetRadiation', 'MergeSeriesFn', 'AverageSeriesByElements', 'CorrectFgForStorage', 'CalculateAvailableEnergy', 'do_qcchecks']
    ds3.globalattributes['Functions'] = l3functions
    # add relevant meteorological values to L3 data
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'AddMetVars' in cf['General']['FunctionList']:
        qcts.AddMetVars(ds3)
    
    # correct measured soil water content using empirical relationship to collected samples
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'CorrectSWC' in cf['General']['FunctionList']:
        qcts.CorrectSWC(cf,ds3)
    
    # apply linear corrections to the data
    qcck.do_linear(cf,ds3)
    
    # merge the HMP and corrected 7500 data
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'MergeSeriesAh' in cf['General']['FunctionList']:
        srclist = qcutils.GetMergeList(cf,'Ah_EC',default=['Ah_HMP_01'])
        qcts.MergeSeries(ds3,'Ah_EC',srclist,[0,10])
    
    # get the air temperature from the CSAT virtual temperature
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'TaFromTv' in cf['General']['FunctionList']:
        qcts.TaFromTv(ds3,'Ta_CSAT','Tv_CSAT','Ah_EC','ps')
    
    # do the 2D coordinate rotation
    qcts.CoordRotation2D(cf,ds3)
    
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'Massman' in cf['General']['FunctionList']:
        # do the Massman frequency attenuation correction to approximate L
        qcts.MassmanApprox(cf,ds3)
        
        # do the Massman frequency attenuation correction
        qcts.Massman(cf,ds3)
    
    # calculate the fluxes
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'Massman' not in cf['General']['FunctionList']:
        qcts.CalculateFluxes(ds3)
    
    # calculate the fluxes from covariances
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'Massman' in cf['General']['FunctionList']:
        qcts.CalculateFluxesRM(ds3)
    
    # approximate wT from virtual wT using wA (ref: Campbell OPECSystem manual)
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'FhvtoFh' in cf['General']['FunctionList']:
        if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='FhvtoFhArgs'):
            attr = ast.literal_eval(cf['FunctionArgs']['FhvtoFhattr'])
            args = ast.literal_eval(cf['FunctionArgs']['FhvtoFhArgs'])
            qcts.FhvtoFh(ds3,args[0],args[1],args[2],args[3],args[4],args[5],args[6],attr)
        else:
            attr = 'Fh rotated and converted from virtual heat flux'
            qcts.FhvtoFh(ds3,'Ta_EC','Fh','Tv_CSAT','Fe_raw','ps','Ah_EC','Fh_rv',attr)
    
    # correct the H2O & CO2 flux due to effects of flux on density measurements
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'Massman' not in cf['General']['FunctionList']:
        qcts.Fe_WPL(ds3,'Fe_wpl','Fe_raw','Fh_rv','Ta_EC','Ah_EC','ps')
        qcts.Fc_WPL(ds3,'Fc_wpl','Fc_raw','Fh_rv','Fe_wpl','Ta_EC','Ah_EC','Cc_7500_Av','ps')
    else:
        qcts.Fe_WPLcov(ds3,'Fe_wpl','wAM','Fh_rmv','Ta_HMP','Ah_HMP','ps')
        qcts.Fc_WPLcov(ds3,'Fc_wpl','wCM','Fh_rmv','wAwpl','Ta_HMP','Ah_HMP','Cc_7500_Av','ps')
    
    # calculate the net radiation from the Kipp and Zonen CNR1
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'CalculateNetRadiation' in cf['General']['FunctionList']:
        srclist = qcutils.GetMergeList(cf,'Fsd',default=['Fsd'])
        qcts.MergeSeries(ds3,'Fsd',srclist,[0,10])
        qcts.CalculateNetRadiation(ds3,'Fn_KZ','Fsd','Fsu','Fld','Flu')
    
    # combine the net radiation from the Kipp and Zonen CNR1 and the NRlite
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'MergeSeriesFn' in cf['General']['FunctionList']:
        srclist = qcutils.GetMergeList(cf,'Fn',default=['Fn_KZ'])
        qcts.MergeSeries(ds3,'Fn',srclist,[0,10])
    
    # interpolate over missing soil moisture values
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'InterpolateOverMissing' in cf['General']['FunctionList']:
        if qcutils.cfkeycheck(cf,Base='FunctionArgs', ThisOne='IOM'):
            qcts.InterpolateOverMissing(ds3,series=ast.literal_eval(cf,['FunctionArgs']['IOM']))
        else:
            qcts.InterpolateOverMissing(ds3,series=ast.literal_eval(cf,['FunctionArgs']['IOM']))
    
    # average the soil heat flux data
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'AverageSeriesByElements' in cf['General']['FunctionList']:
        srclist = qccf.GetAverageList(cf,'Fg_01',default=['Fg_01a'])
        qcts.AverageSeriesByElements(ds3,'Fg_01',srclist)
        # average the soil temperature data
        
        srclist = qccf.GetAverageList(cf,'Ts_01',default=['Ts_01a'])
        qcts.AverageSeriesByElements(ds3,'Ts_01',srclist)
        # average soil moisture
        
        slist = [l for l in cf['Variables'].keys() if 'Sws_' in l]
        for ThisOne in slist:
            if ThisOne in cf['Variables'].keys() and 'AverageSeries' in cf['Variables'][ThisOne].keys():
                srclist = qccf.GetAverageList(cf,ThisOne)
                qcts.AverageSeriesByElements(ds3,ThisOne,srclist)
    
    # correct the measured soil heat flux for storage in the soil layer above the sensor
    args = ast.literal_eval(cf['FunctionArgs']['CFg1Args'])
    if len(args) == 4:
        qcts.CorrectFgForStorage(cf,ds3,args[0],args[1],args[2],args[3])
    else:
        qcts.CorrectFgForStorage(cf,ds3,args[0],args[1],args[2])
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='CFg2Args'):
        args = ast.literal_eval(cf['FunctionArgs']['CFg2Args'])
        if len(args) == 4:
            qcts.CorrectFgForStorage(cf,ds3,args[0],args[1],args[2],args[3])
        else:
            qcts.CorrectFgForStorage(cf,ds3,args[0],args[1],args[2])
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='CFg3Args'):
        args = ast.literal_eval(cf['FunctionArgs']['CFg3Args'])
        if len(args) == 4:
            qcts.CorrectFgForStorage(cf,ds3,args[0],args[1],args[2],args[3])
        else:
            qcts.CorrectFgForStorage(cf,ds3,args[0],args[1],args[2])
    
    # average soil measurements
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='A3SBE_1_in'):
        in1args = ast.literal_eval(cf['FunctionArgs']['A3SBE_1_in'])
        out1arg = ast.literal_eval(cf['FunctionArgs']['A3SBE_1_out'])
        qcts.Average3SeriesByElements(ds3,out1arg[0],in1args)
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='A3SBE_2_in'):
        in2args = ast.literal_eval(cf['FunctionArgs']['A3SBE_2_in'])
        out2arg = ast.literal_eval(cf['FunctionArgs']['A3SBE_2_out'])
        qcts.Average3SeriesByElements(ds3,out2arg[0],in2args)
    if qcutils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='A3SBE_3_in'):
        in3args = ast.literal_eval(cf['FunctionArgs']['A3SBE_3_in'])
        out3arg = ast.literal_eval(cf['FunctionArgs']['A3SBE_3_out'])
        qcts.Average3SeriesByElements(ds3,out3arg[0],in3args)
    
    # calculate the available energy
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='FunctionList') and 'CalculateAvailableEnergy' in cf['General']['FunctionList']:
        qcts.CalculateAvailableEnergy(ds3,'Fa','Fn','Fg')
    
    # re-apply the quality control checks (range, diurnal and rules)
    qcck.do_qcchecks(cf,ds3)
    
    # coordinate gaps in the three main fluxes
    if qcutils.cfkeycheck(cf,Base='General',ThisOne='Functions') and 'gaps' in cf['General']['FunctionList']:
        qcck.gaps(cf,ds3)
    
    return ds3

def l4qc_FillMetGaps(cf,ds3):
    """
        Fill gaps in met data from other sources
        Generates L4 from L3 data
        
        Variable Series:
            Meteorological (MList): Ah_EC, Cc_7500_Av, ps, Ta_EC, Ws_CSAT, Wd_CSAT
            Radiation (RList): Fld, Flu, Fn, Fsd, Fsu
            Soil water content (SwsList): all variables containing Sws in variable name
            Soil (SList): Fg, Ts, SwsList
            Turbulent fluxes (FList): Fc_wpl, Fe_wpl, Fh, ustar
            Output (OList): MList, RList, SList, FList
        
        Parameters loaded from control file:
            zmd: z-d
            z0: roughness height
        
        Functions performed:
            qcts.InterpolateOverMissing (OList for gaps shorter than 3 observations, OList gaps shorter than 7 observations)
            qcts.GapFillFromAlternate (MList, RList)
            qcts.GapFillFromClimatology (Ah_EC, Fn, Fg, ps, Ta_EC, Ws_CSAT, OList)
            qcts.GapFillFromRatios (Fe, Fh, Fc)
            qcts.ReplaceOnDiff (Ws_CSAT, ustar)
            qcts.UstarFromFh
            qcts.ReplaceWhereMissing (Ustar)
            qcck.do_qcchecks
        """
    level = 'L4'    # level of processing
    # get z-d (measurement height minus displacement height) and z0 from the control file
    zmd = float(cf['General']['zmd'])   # z-d for site
    z0 = float(cf['General']['z0'])     # z0 for site
    # make a copy of the L4 data, data from the alternate sites will be merged with this copy
    ds4 = copy.deepcopy(ds3)
    ds4.globalattributes['Level'] = level
    ds4.globalattributes['EPDversion'] = sys.version
    ds4.globalattributes['QCVersion'] = __doc__
    ds4.globalattributes['Functions'] = 'InterpolateOverMissing, GapFillFromAlternate, GapFillFromClimatology, GapFillFromRatios, ReplaceOnDiff, UstarFromFh, ReplaceWhereMissing, do_qcchecks'
    # linear interpolation to fill missing values over gaps of 1 hour
    qcts.InterpolateOverMissing(cf,ds4,maxlen=2)
    # gap fill meteorological and radiation data from the alternate site(s)
    log.info(' Gap filling using data from alternate sites')
    qcts.GapFillFromAlternate(cf,ds4)
    # gap fill meteorological, radiation and soil data using climatology
    log.info(' Gap filling using site climatology')
    qcts.GapFillFromClimatology(cf,ds4)
    # gap fill using neural networks
    # qcts.GapFillFluxesUsingNN(cf,ds4)
    # gap fill using "match and replace"
    # qcts.GapFillFluxesUsingMR(cf,ds4)
    # gap fill using evaporative fraction (Fe/Fa), Bowen ratio (Fh/Fe) and ecosystem water use efficiency (Fc/Fe)
    log.info(' Gap filling Fe, Fh and Fc using ratios')
    qcts.GapFillFromRatios(cf,ds4)
    # !!! this section required for Daly Uncleared 2009 to deal with bad CSAT from 14/4/2009 to 22/10/2009 !!!
    # replace wind speed at Daly Uncleared when it differs from alternate site by more than threshold
    log.info(' Replacing Ws_CSAT when difference with alternate data exceeds threshold')
    qcts.ReplaceOnDiff(cf,ds4,series=['Ws_CSAT'])
    # calculate u* from Fh and corrected wind speed
    qcts.UstarFromFh(ds4,'uscalc','Ta_EC', 'Ah_EC', 'ps', 'Fh', 'Ws_CSAT', zmd, z0)
    qcts.ReplaceWhereMissing(ds4.series['ustar'],ds4.series['ustar'],ds4.series['uscalc'],0)
    # !!! this section required for Daly Uncleared 2009 to deal with bad CSAT from 14/4/2009 to 22/10/2009 !!!
    # replace measured u* with calculated u* when difference exceeds threshold
    log.info(' Replacing ustar when difference with alternate data exceeds threshold')
    qcts.ReplaceOnDiff(cf,ds4,series=['ustar'])
    # re-apply the quality control checks (range, diurnal and rules)
    log.info(' Doing QC checks on L4 data')
    qcck.do_qcchecks(cf,ds4)
    # interpolate over any ramaining gaps up to 3 hours in length
    qcts.InterpolateOverMissing(cf,ds4,maxlen=6)
    # fill any remaining gaps climatology
    qcts.GapFillFromClimatology(cf,ds4)
    return ds4

def l4qc_GapFilledFluxes(cf,ds3):
    """
        Integrate SOLO-ANN gap filled fluxes performed externally
        Generates L4 from L3 data
        Generates daily sums excel workbook
        
        Functions performed:
            qcts.AddMetVars
            qcts.ComputeDailySums
        """
    # make a copy of the L4 data
    ds4 = copy.deepcopy(ds3)
    ds4.globalattributes['Level'] = 'L4'
    ds4.globalattributes['EPDversion'] = sys.version
    ds4.globalattributes['QCVersion'] = __doc__
    ds4.globalattributes['Functions'] = 'SOLO ANN GapFilling 10-day window, AddMetVars, ComputeDailySums (not included)'
    # duplicate gapfilled fluxes for graphing comparison
    Fe,flag = qcutils.GetSeriesasMA(ds4,'Fe_gapfilled')
    qcutils.CreateSeries(ds4,'Fe_wpl',Fe,Flag=flag,Descr='ANN gapfilled Fe',Units='W/m2')
    Fc,flag = qcutils.GetSeriesasMA(ds4,'Fc_gapfilled')
    qcutils.CreateSeries(ds4,'Fc_wpl',Fc,Flag=flag,Descr='ANN gapfilled Fc',Units='mg/m2/s')
    Fh,flag = qcutils.GetSeriesasMA(ds4,'Fh_gapfilled')
    qcutils.CreateSeries(ds4,'Fh_rmv',Fh,Flag=flag,Descr='ANN gapfilled Fh',Units='W/m2')
    # add relevant meteorological values to L3 data
    qcts.AddMetVars(ds4)
    # compute daily statistics
    qcts.ComputeDailySums(cf,ds4)
    return ds4
