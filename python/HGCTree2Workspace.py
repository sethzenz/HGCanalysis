#!/usr/bin/env python

import ROOT
import numpy as numpy
import json
import os

from UserCode.HGCanalysis.PlotUtils import *

"""
Converts all to a workspace and computes optimized weights
"""
def prepareWorkspace(url,integRanges,treeVarName,vetoTrackInt,vetoHEBLeaks=False,addRaw=False):

    #optimization with linear regression
    optimVec = numpy.zeros( len(integRanges) )
    optimMatrix = numpy.zeros( (len(integRanges), len(integRanges) ) )
 
    #prepare the workspace
    outUrl=os.path.basename(url).replace('.root','')
    os.system('mkdir -p %s'%outUrl)
    ws=ROOT.RooWorkspace("w")
    dsVars=ROOT.RooArgSet( ws.factory('eta[1.5,1.45,3.1]'), 
                           ws.factory('en[0,0,9999999999]'), 
                           ws.factory('phi[0,-3.2,3.2]'),
                           ws.factory('length[0,0,9999999.]'), 
                           ws.factory('volume[0,0,9999999.]') )
    for ireg in xrange(0,len(integRanges)): dsVars.add( ws.factory('edep%d[0,0,99999999]'%ireg) )
    if addRaw : 
        for ilay in xrange(1,55):
            dsVars.add( ws.factory('rawedep%d[0,0,99999999]'%ilay) )
    getattr(ws,'import')( ROOT.RooDataSet('data','data',dsVars) )

    #read all to a RooDataSet
    if url.find('/store/')>=0: url='root://eoscms//eos/cms/%s'%url
    fin=ROOT.TFile.Open(url)
    HGC=fin.Get('analysis/HGC')
    simStep=treeVarName.split('_')[1]
    print 'Updating status every 1k events read / %dk events available'%(HGC.GetEntriesFast()/1000)
    for entry in xrange(0,HGC.GetEntriesFast()+1):
        HGC.GetEntry(entry)
        if entry%1000==0 : drawProgressBar(float(entry)/float(HGC.GetEntriesFast()))

        #veto interactions in the tracker
        if vetoTrackInt and HGC.hasInteractionBeforeHGC : continue

        #require generated particle to be in the endcap
        genEn=HGC.genEn
        genEta=ROOT.TMath.Abs(HGC.genEta)
        genPhi=HGC.genPhi
        if genEta<1.4 or genEta>3.0 : continue
        ws.var('en').setVal(genEn)
        ws.var('eta').setVal(genEta)
        ws.var('phi').setVal(genPhi)
        showerLength,showerVolume=0,0
        try:
            showerLength, showerVolume=getattr(HGC,'totalLength_%s'%(simStep)),getattr(HGC,'totalVolume_%s'%(simStep))
        except:
            pass
        ws.var('length').setVal(showerLength)
        ws.var('volume').setVal(showerVolume)
        newEntry=ROOT.RooArgSet(ws.var('en'), ws.var('eta'),  ws.var('phi'), ws.var('length'), ws.var('volume') )

        #showerMeanEta=getattr(HGC,'showerMeanEta_%s'%simStep)
        showerMeanEta=genEta
        #geomCorrection=ROOT.TMath.TanH(genEta)
        geomCorrection=1./ROOT.TMath.TanH(showerMeanEta)
        
        #check the amount of energy deposited in the back HEB
        if vetoHEBLeaks:
            sumBackHEB=0
            for ilayer in [51,52,53]:
                sumBackHEB+=(getattr(HGC,treeVarName))[ilayer-1]
            if sumBackHEB>3: continue

        #get the relevant energy deposits and add new row
        for ireg in xrange(0,len(integRanges)):
            totalEnInIntegRegion=0           
            for ilayer in xrange(integRanges[ireg][0],integRanges[ireg][1]+1):
                irawEdep=(getattr(HGC,treeVarName))[ilayer-1]
                totalEnInIntegRegion=totalEnInIntegRegion+irawEdep
                if addRaw:
                    ws.var('rawedep%d'%ilayer).setVal(irawEdep*geomCorrection)
                    newEntry.add(ws.var('rawedep%d'%ilayer))

            ws.var('edep%d'%ireg).setVal(totalEnInIntegRegion*geomCorrection)
            newEntry.add(ws.var('edep%d'%(ireg)))

        ws.data('data').add( newEntry )

        #for optimization
        for ie in xrange(0,len(integRanges)):
            optimVec[ie]=optimVec[ie]+ws.var('edep%d'%ie).getVal()/genEn
            for je in xrange(0,len(integRanges)):
                optimMatrix[ie][je]=optimMatrix[ie][je]+ws.var('edep%d'%ie).getVal()*ws.var('edep%d'%je).getVal()/(genEn*genEn)


    fin.Close()

    #finalize optimization
    try:
        optimWeights=numpy.linalg.solve(optimMatrix,optimVec)
        optimData={}
        optimData['IntegrationRanges'] = [ {'first':fLayer, 'last':lLayer} for fLayer,lLayer in integRanges ]
        optimData['OptimWeights'] = [ item for item in optimWeights ]
        with io.open('%s/optim_weights.dat'%outUrl, 'w', encoding='utf-8') as f: f.write(unicode(json.dumps(optimData, sort_keys = True, ensure_ascii=False, indent=4)))
    except:
        print 'Failed to optimize - singular matrix?'
        print 'Matrix: ',optimMatrix
        print 'Vector: ',optimVec

    #all done, write to file
    wsFileUrl='%s/workspace.root'%outUrl
    ws.writeToFile(wsFileUrl,True)
    print 'Created the analysis RooDataSet with %d events, stored @ %s'%(ws.data('data').numEntries(),wsFileUrl)
    return wsFileUrl

"""
Helper function to show and save the results of the fit to a slice
"""
def showCalibrationFitResults(theVar,theData,thePDF,theLabel,fitName,outDir) :
    canvas=ROOT.TCanvas('c','c',500,500)
    
    pframe=theVar.frame(ROOT.RooFit.Range(fitName))
    theData.plotOn(pframe)
    thePDF.plotOn(pframe,ROOT.RooFit.Range(fitName))
    pframe.Draw()
    pframe.GetXaxis().SetTitle(theVar.GetTitle())
    pframe.GetYaxis().SetTitle('Events')
    pframe.GetYaxis().SetTitleOffset(1.2)
    pframe.GetYaxis().SetRangeUser(0.01,1.8*pframe.GetMaximum())
    pframe.GetXaxis().SetNdivisions(5)
    MyPaveText(theLabel,0.15,0.95,0.5,0.7).SetTextSize(0.035)
    MyPaveText('#bf{CMS} #it{simulation}')
    canvas.SaveAs('%s/%s.png'%(outDir,fitName))

"""
shows a set of calibration curves
"""
def showCalibrationCurves(calibGr,calibRanges,outDir,calibPostFix) :
    canvas=ROOT.TCanvas('c','c',500,500)
    canvas.cd()
    up=ROOT.TPad('up','up',0.0,0.4,1.0,1.0)
    up.SetBottomMargin(0.01)
    up.SetTopMargin(0.08)
    up.Draw()
    up.cd()
    leg=ROOT.TLegend(0.8,0.6,0.9,0.9)
    leg.SetFillStyle(0)
    leg.SetBorderSize(0)
    leg.SetTextFont(42)
    leg.SetTextSize(0.045)
    resCalibGr={}
    resCorrectionGr={}
    igr=0
    for wType in calibGr:
        if igr==0:
            calibGr[wType].Draw('a')
            calibGr[wType].GetXaxis().SetTitleSize(0)
            calibGr[wType].GetXaxis().SetLabelSize(0)
            calibGr[wType].GetYaxis().SetTitle('Reconstructed energy')
            calibGr[wType].GetYaxis().SetTitleOffset(0.9)
            calibGr[wType].GetYaxis().SetTitleSize(0.07)
            calibGr[wType].GetYaxis().SetLabelSize(0.05)
            calibGr[wType].GetYaxis().SetRangeUser(1,calibGr[wType].GetYaxis().GetXmax()*2)
            for gr in calibGr[wType].GetListOfGraphs():
                leg.AddEntry(gr,gr.GetTitle(),"p")
        else:
            calibGr[wType].Draw()
        igr+=1

        lcol=calibGr[wType].GetListOfGraphs().At(0).GetLineColor()
        ffunc=calibGr[wType].GetListOfFunctions().At(0)
        ffunc.SetLineColor(lcol)
        ffunc.SetLineStyle(9)
        calib_offset=ffunc.GetParameter(1)
        calib_slope=ffunc.GetParameter(0)
        MyPaveText('#it{%s} : %3.4f E_{rec} + %3.4f'%(calibGr[wType].GetTitle(),1./calib_slope,-calib_offset/calib_slope),
                   0.15,0.95-igr*0.05,0.4,0.92-igr*0.05).SetTextColor(lcol)

        #compute the residuals
        resCalibGr[wType]=ROOT.TMultiGraph()
        resCorrectionGr[wType]=None
        for gr in calibGr[wType].GetListOfGraphs() :

            newGr=gr.Clone('%s_res'%gr.GetName())
            newGr.Set(0)
            xval, yval = ROOT.Double(0), ROOT.Double(0)
            for ip in xrange(0,gr.GetN()):
                gr.GetPoint(ip,xval,yval)
                xval_error=gr.GetErrorX(ip)
                yval_error=gr.GetErrorY(ip)
                xrec=(yval-calib_offset)/calib_slope
                xrec_error=yval_error/calib_slope
                newGr.SetPoint(ip,xval,100*(xrec/xval-1))
                newGr.SetPointError(ip,xval_error,100*xrec_error/xval)
            resCalibGr[wType].Add(newGr,'p')

            #linear approximation to residuals
            newGr.Fit('pol0','QME0+')
            if resCorrectionGr[wType] is None:
                resCorrectionGr[wType]=gr.Clone('%s_calib_residuals'%wType)
                resCorrectionGr[wType].SetTitle(calibGr[wType].GetTitle())
                resCorrectionGr[wType].Set(0)
            ip=resCorrectionGr[wType].GetN()
            calibXmin=calibRanges[ip][0]
            calibXmax=calibRanges[ip][1]
            resCorrectionGr[wType].SetPoint(ip,0.5*(calibXmax+calibXmin),newGr.GetFunction('pol0').GetParameter(0)/100.)
            resCorrectionGr[wType].SetPointError(ip,0.5*(calibXmax-calibXmin),newGr.GetFunction('pol0').GetParError(0)/100.)

    leg.Draw()
    MyPaveText('#bf{CMS} #it{simulation}').SetTextSize(0.06)

    canvas.cd()
    dp=ROOT.TPad('dp','dp',0.0,0.0,1.0,0.4)
    dp.SetTopMargin(0.01)
    dp.SetBottomMargin(0.2)
    dp.Draw()
    dp.cd()
    igr=0
    for wType in resCalibGr:
        if igr==0:
            resCalibGr[wType].Draw('a')
            resCalibGr[wType].GetYaxis().SetRangeUser(-6.5,6.5)
            resCalibGr[wType].GetYaxis().SetNdivisions(5)
            resCalibGr[wType].GetXaxis().SetTitle('Generated energy [GeV]')
            resCalibGr[wType].GetYaxis().SetTitle('<E_{rec}-E_{gen}>/E_{gen} [%]')
            resCalibGr[wType].GetYaxis().SetTitleOffset(0.7)
            resCalibGr[wType].GetYaxis().SetTitleSize(0.09)
            resCalibGr[wType].GetYaxis().SetLabelSize(0.07)
            resCalibGr[wType].GetXaxis().SetTitleSize(0.09)
            resCalibGr[wType].GetXaxis().SetLabelSize(0.08)
        else:
            resCalibGr[wType].Draw()
        igr+=1

    canvas.cd()
    canvas.Modified()
    canvas.Update()
    canvas.SaveAs('%s/calib%s.png'%(outDir,calibPostFix))
    up.Delete()
    dp.Delete()

    #now show residual calibration
    canvas.Clear()
    igr=0
    leg=ROOT.TLegend(0.2,0.7,0.9,0.9)
    leg.SetFillStyle(0)
    leg.SetBorderSize(0)
    leg.SetTextFont(42)
    leg.SetTextSize(0.035)
    for wType in resCorrectionGr:
        if igr==0:
            resCorrectionGr[wType].Draw('ap')
            resCorrectionGr[wType].GetXaxis().SetTitle('Pseudo-rapidity')
            resCorrectionGr[wType].GetYaxis().SetTitle('Residual correction')
            resCorrectionGr[wType].GetYaxis().SetTitleOffset(0.9)
            resCorrectionGr[wType].GetYaxis().SetTitleSize(0.05)
            resCorrectionGr[wType].GetYaxis().SetLabelSize(0.04)
            resCorrectionGr[wType].GetXaxis().SetTitleOffset(0.9)
            resCorrectionGr[wType].GetXaxis().SetTitleSize(0.05)
            resCorrectionGr[wType].GetXaxis().SetLabelSize(0.04)
            resCorrectionGr[wType].GetYaxis().SetRangeUser(-1.5*resCorrectionGr[wType].GetYaxis().GetXmax(),resCorrectionGr[wType].GetYaxis().GetXmax()*1.5)
        else:
            resCorrectionGr[wType].Draw('p')
        leg.AddEntry(resCorrectionGr[wType],resCorrectionGr[wType].GetTitle(),"p")
        igr+=1
    leg.Draw()
    MyPaveText('#bf{CMS} #it{simulation}').SetTextSize(0.04)
    canvas.cd()
    canvas.Modified()
    canvas.Update()
    canvas.SaveAs('%s/rescalib%s.png'%(outDir,calibPostFix))
    
    return resCorrectionGr,resCalibGr
    

"""
shows a set of resolution curves
"""
def showResolutionCurves(resGr,outDir,calibPostFix,model=0) :

    resolModel=None
    if model==0  : resolModel=ROOT.TF1('resolmodel',"sqrt([0]*[0]/x+[1]*[1])",0,1000)
    else : 
        resolModel=ROOT.TF1('resolmodel',"sqrt([0]*[0]/x+[1]*[1]+[2]*[2]/(x*x))",0,1000)
        resolModel.SetParameter(2,0)
        resolModel.SetParLimits(2,0.05,0.1)
    resolModel.SetParameter(0,0.2);
    resolModel.SetParLimits(0,0,2);
    resolModel.SetParameter(1,0);
    resolModel.SetParLimits(1,0,1.0);

    canvas=ROOT.TCanvas('c','c',500,500)
    canvas.cd()
    leg=ROOT.TLegend(0.75,0.5,0.9,0.95)
    leg.SetFillStyle(0)
    leg.SetBorderSize(0)
    leg.SetTextFont(42)
    leg.SetTextSize(0.03)

    igr=0
    pt=[]
    for wType in resGr:
        if igr==0:
            resGr[wType].Draw('a')
            resGr[wType].GetXaxis().SetTitleSize(0)
            resGr[wType].GetXaxis().SetLabelSize(0)
            resGr[wType].GetXaxis().SetTitle('Generated energy [GeV]')
            resGr[wType].GetYaxis().SetTitle('#sigma_{E} / E')
            resGr[wType].GetYaxis().SetTitleOffset(1.3)
            resGr[wType].GetYaxis().SetTitleSize(0.07)
            resGr[wType].GetYaxis().SetLabelSize(0.05)
            resGr[wType].GetYaxis().SetRangeUser(1,resGr[wType].GetYaxis().GetXmax()*2)
            for gr in resGr[wType].GetListOfGraphs():
                leg.AddEntry(gr,gr.GetTitle(),"p")
        else:
            resGr[wType].Draw()
        igr+=1

        lcol=resGr[wType].GetListOfGraphs().At(0).GetLineColor()
        resGr[wType].Fit(resolModel,'MER+')
        ffunc=resGr[wType].GetListOfFunctions().At(0)
        ffunc.SetLineStyle(9)
        ffunc.SetLineColor(lcol)
        sigmaStoch    = ffunc.GetParameter(0)
        sigmaStochErr = ffunc.GetParError(0)
        sigmaConst    = ffunc.GetParameter(1)
        sigmaConstErr = ffunc.GetParError(1)
        if model==0 :
            pt.append( MyPaveText('#it{%s} :  %3.4f#scale[0.8]{/#sqrt{E}} #oplus %3.4f'%(resGr[wType].GetTitle(),sigmaStoch,sigmaConst),
                                  0.2,0.93-igr*0.05,0.4,0.90-igr*0.05) )
        else :
            sigmaNoise = ffunc.GetParameter(2)
            pt.append( MyPaveText('#it{%s} :  %3.4f#scale[0.8]{/#sqrt{E}} #oplus %3.4f#scale[0.8]{/E} #oplus %3.4f'%(resGr[wType].GetTitle(),sigmaStoch,sigmaNoise,sigmaConst),
                                  0.2,0.93-igr*0.05,0.4,0.90-igr*0.05) )
        pt[igr-1].SetTextColor(lcol)
        pt[igr-1].SetTextSize(0.03)

    leg.Draw()
    MyPaveText('#bf{CMS} #it{simulation}').SetTextSize(0.04)

    canvas.Modified()
    canvas.Update()
    canvas.SaveAs('%s/resol%s.png'%(outDir,calibPostFix))
    canvas.SaveAs('%s/resol%s.C'%(outDir,calibPostFix))
