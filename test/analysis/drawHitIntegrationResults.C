#include "TROOT.h"
#include "TStyle.h"
#include "TFile.h"
#include "TCanvas.h"
#include "TString.h"
#include "TPaveText.h"
#include "TLegend.h"
#include "TH1F.h"
#include "TObjArray.h"
#include "TGraphErrors.h"
#include "TMath.h"
#include "TF1.h"

void showCanvas(TObjArray plots,TString name,TString title,TString outDir);

void fixExtremities(TH1F* h,bool addOverflow, bool addUnderflow)
{
  if(h==0) return;

  if(addUnderflow){
      double fbin  = h->GetBinContent(0) + h->GetBinContent(1);
      double fbine = sqrt(h->GetBinError(0)*h->GetBinError(0)
                          + h->GetBinError(1)*h->GetBinError(1));
      h->SetBinContent(1,fbin);
      h->SetBinError(1,fbine);
      h->SetBinContent(0,0);
      h->SetBinError(0,0);
    }
  
  if(addOverflow){  
      int nbins = h->GetNbinsX();
      double fbin  = h->GetBinContent(nbins) + h->GetBinContent(nbins+1);
      double fbine = sqrt(h->GetBinError(nbins)*h->GetBinError(nbins) 
                          + h->GetBinError(nbins+1)*h->GetBinError(nbins+1));
      h->SetBinContent(nbins,fbin);
      h->SetBinError(nbins,fbine);
      h->SetBinContent(nbins+1,0);
      h->SetBinError(nbins+1,0);
    }
}


//
void drawHitIntegrationResults(TString inURL="IntegrateHits_trackExtrapolation.root",TString outDir="~/www/HGCal/HitIntegration/v5")
{
  TString dists[]=
    {
      //   "ntothits",   "nhits",
      "hitwgtdy",//   "hitdy",
      "hitwgtdx",//   "hitdx",
      //      "hitwgtdz",   "hitdz",
      // "simhiten",   //"simhittoten"
      //"simhitenit", "simhittotenit",
      //"hitadc",     "hittotadc",
      //"hitalpha"
    };

  TFile *_file0 = TFile::Open(inURL);

  gROOT->SetBatch(true);
  gStyle->SetOptStat(0);
  gStyle->SetOptTitle(0);
  for(size_t idist=0; idist<sizeof(dists)/sizeof(TString); idist++)
    {  
      
      bool doGaussFit(false);
      if(dists[idist].EndsWith("dz") || dists[idist].EndsWith("dx") || dists[idist].EndsWith("dy")) doGaussFit=true;
      
      TGraphErrors *profileInSD=new TGraphErrors;      profileInSD->SetName("profileinsd");         profileInSD->SetTitle("SR");      profileInSD->SetMarkerStyle(20); profileInSD->SetLineWidth(2);
      TGraphErrors *profileInSD_ctrl=new TGraphErrors; profileInSD_ctrl->Clone("profileinsd_ctrl"); profileInSD_ctrl->SetTitle("CR"); profileInSD_ctrl->SetMarkerStyle(24);
      for(size_t isd=0;isd<=2; isd++)
	{
	  size_t nlayers(30);
	  TString sdName("EE");
	  if(isd==1) {sdName="HEfront"; nlayers=12; }
	  if(isd==2) {sdName="HEback";  nlayers=12; }

	  TH1F *totalInSD=0,*totalInSD_ctrl=0;
	  for(size_t ilayer=1; ilayer<=nlayers; ilayer++)
	    {
	      TString pfix("sd"); pfix += isd; pfix += "_lay"; pfix += ilayer; pfix += "_";
	     
	      //get histograms
	      TString dist(pfix+dists[idist]);
	      TH1F *h=(TH1F *)_file0->Get(dist);
	      fixExtremities(h,true,true);
	      h->SetTitle("SR");
	      h->SetLineWidth(2);
	      Float_t avg(h->GetMean());
	      Float_t avgErr(h->GetMeanError());
	      if(doGaussFit)
		{
		  h->Fit("gaus","RM+","",-10,10);
		  TF1 *gaus=h->GetFunction("gaus");
		  cout << gaus << endl;
		  avg=gaus->GetParameter(1);
		  avgErr=gaus->GetParameter(2);
		}

	      TString dist_ctrl(pfix+"ctrl_"+dists[idist]);

	      TH1F *h_ctrl=(TH1F *)_file0->Get(dist_ctrl);
	      fixExtremities(h_ctrl,true,true);
	      h_ctrl->SetTitle("CR");
	      h_ctrl->SetLineWidth(1);
	      h_ctrl->SetFillColor(kCyan-3);
	      h_ctrl->SetFillStyle(1001);
	      Float_t avg_ctrl(h_ctrl->GetMean());
	      Float_t avgErr_ctrl(h_ctrl->GetMeanError());
	      if(doGaussFit)
		{
		  h_ctrl->Fit("gaus","RM+","",-10,10);
		  TF1 *gaus=h_ctrl->GetFunction("gaus");
		  cout << gaus << endl;
		  avg_ctrl=gaus->GetParameter(1);
		  avgErr_ctrl=gaus->GetParameter(2);
		}
	      //accumulate
	      if(totalInSD==0)
		{
		  totalInSD=(TH1F *)h->Clone("totalinsd"); 
		  totalInSD->SetDirectory(0);
		  totalInSD->Reset("ICE");
		  totalInSD_ctrl=(TH1F *)h_ctrl->Clone("totalinsd_ctrl"); 
		  totalInSD_ctrl->SetDirectory(0);
		  totalInSD_ctrl->Reset("ICE");
		}
	      totalInSD->Add(h);
	      totalInSD_ctrl->Add(h_ctrl);

	      //profile
	      Int_t np=profileInSD->GetN();
	      profileInSD->SetPoint(np,np+1,avg);
	      profileInSD->SetPointError(np,0,avgErr);
	      profileInSD_ctrl->SetPoint(np,np+1,avg_ctrl);
	      profileInSD_ctrl->SetPointError(np,0,avgErr_ctrl);

	      TObjArray plots; 
	      plots.Add(h_ctrl);
	      plots.Add(h); 
	      TString title(sdName + ", layer=");
	      title += ilayer;
	      showCanvas(plots,dist,title,outDir);
	    }
	  
	  TString pfix("sd"); pfix += isd; pfix += "_inc_";
	  TObjArray plots; 
	  plots.Add(totalInSD_ctrl);
	  plots.Add(totalInSD);
	  TString title(sdName + ", inclusive");
	  showCanvas(plots,pfix+dists[idist],title,outDir);
	}
      
      TObjArray plots; 
      plots.Add(profileInSD_ctrl);
      plots.Add(profileInSD);
      TString title("");
      showCanvas(plots,"prof_"+dists[idist],title,outDir);
    }
}

//
void showCanvas(TObjArray plots,TString name,TString title,TString outDir)
{
  TCanvas *c=new TCanvas("c","c",500,500);
  c->SetLeftMargin(0.15);
  c->SetTopMargin(0.05);
  c->SetRightMargin(0.05);
  c->SetBottomMargin(0.12);

  TLegend *leg=new TLegend(0.15,0.8,0.7,0.94);
  leg->SetBorderSize(0);
  leg->SetFillStyle(0);
  leg->SetTextFont(42);
  leg->SetTextSize(0.04);

  //check range to draw
  Double_t ymin(9999999.),ymax(-ymin);
  for(Int_t i=0; i<plots.GetEntriesFast(); i++)
    {
      TObject *obj=plots.At(i);
      TString className=obj->ClassName();
      if(className.Contains("TH1")) 
	{
	  TH1 *h=(TH1 *)obj;
	  ymin=TMath::Min(ymin,h->GetMinimum());
	  ymax=TMath::Max(ymax,h->GetMaximum());
	}
      else if(className.Contains("TGraph"))
	{
	  TGraphErrors *gr=(TGraphErrors *)obj;
	  ymin=TMath::Min(ymin,TMath::MinElement(gr->GetN(),gr->GetY()));
	  ymax=TMath::Max(ymax,TMath::MaxElement(gr->GetN(),gr->GetY()));
	}
    }
  if(ymin<0) ymin*=1.5;    else ymin*=0.25;
  if(ymax<0) ymax*=0.25;   else ymax*=1.5;

  //draw
  for(Int_t i=0; i<plots.GetEntriesFast(); i++)
    {
      TObject *obj=plots.At(i);
      TString className=obj->ClassName();
      if(className.Contains("TH1")) 
	{
	  TH1 *h=(TH1 *)obj;
	  h->Draw(i==0 ? "hist" : "histsame");
	  h->GetYaxis()->SetRangeUser(ymin,ymax);
	  h->GetYaxis()->SetTitleOffset(1.4);
	  h->GetXaxis()->SetTitleSize(0.05);
	  h->GetXaxis()->SetLabelSize(0.04);
	  h->GetYaxis()->SetTitleSize(0.05);
	  h->GetYaxis()->SetLabelSize(0.04);
	  leg->AddEntry(h,h->GetTitle(),"lf");
	}
      else if(className.Contains("TGraph"))
	{
	  TGraphErrors *gr=(TGraphErrors *)obj;
	  gr->Draw(i==0 ? "ap" : "p");
	  gr->GetXaxis()->SetTitle("HGC layer number");
	  gr->GetYaxis()->SetRangeUser(ymin,ymax);
	  gr->GetXaxis()->SetTitleSize(0.05);
	  gr->GetXaxis()->SetLabelSize(0.04);
	  gr->GetYaxis()->SetTitleSize(0.05);
	  gr->GetYaxis()->SetLabelSize(0.04);
	  leg->AddEntry(gr,gr->GetTitle(),"p");
	}
    }
  leg->Draw();
  
  TPaveText *pt=new TPaveText(0.12,0.96,0.6,0.99,"brNDC");
  pt->SetBorderSize(0);
  pt->SetFillStyle(0);
  pt->SetTextFont(42);
  pt->SetTextAlign(12);
  pt->SetTextSize(0.04);
  pt->AddText("CMS simulation");
  pt->Draw();

  if(title!="")
    {
      pt=new TPaveText(0.65,0.955,0.95,0.99,"brNDC");
      pt->SetBorderSize(1);
      pt->SetFillStyle(0);
      pt->SetTextFont(42);
      pt->SetTextAlign(12);
      pt->SetTextSize(0.035);
      pt->AddText(title);
      pt->Draw();
    }
  
  
  c->SaveAs(outDir+"/"+name+".png");
}