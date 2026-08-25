# Kokaly 2011 — PRISM / MICA (USGS)

- 源文件: D:\CRAMM\kokaly2011.pdf
- 页数: 4
- 标题: MAPPING THE DISTRIBUTION OF MATERIALS IN HYPERSPECTRAL DATA USING THE USGS MATERIAL IDENTIFICATION AND CHARACTERIZATION ALGORITHM (MICA)

---


<!-- page 1 -->

MAPPING THE DISTRIBUTION OF MATERIALS IN HYPERSPECTRAL 
DATA USING THE USGS MATERIAL IDENTIFICATION AND 
CHARACTERIZATION ALGORITHM (MICA) 
 
Raymond F. Kokaly, Trude V.V. King, and Todd M. Hoefen 
U.S. Geological Survey 
 
1. INTRODUCTION 
Identifying materials by measuring and 
analyzing their reflectance spectra has been an 
important method in analytical chemistry for 
decades. Airborne and space-based imaging 
spectrometers allow scientists to detect materials and 
map their distributions across the landscape.  With 
new satellite-borne hyperspectral sensors planned 
for the future, for example, HYSPIRI 
(HYPerspectral InfraRed Imager), robust methods 
are needed to fully exploit the information content of 
hyperspectral remote sensing data. A method of 
identifying and mapping materials using spectral-
feature based analysis of reflectance data in an 
expert-system framework called MICA (Material 
Identification and Characterization Algorithm) is 
described in this paper. The core concepts and 
calculations of MICA are presented. A MICA 
command file has been developed and applied to 
map minerals in the full-country coverage of the 
2007 Afghanistan HyMap hyperspectral data.  
 
2. BACKGROUND AND KEY CONCEPTS OF 
MICA
MICA draws on the legacies of a variety of 
U.S Geological Survey (USGS) software that has 
been created to advance spectroscopy and 
spectroscopic remote sensing, including SPECPR 
[1] and Tetracorder [2]. MICA is written in IDL 
(Interactive Data Language) to run within ENVI 
(Environment for Visualizing Images). Maps created 
by MICA are easily integrated with the image 
processing and GIS (Geographic Information 
Systems) capabilities of ENVI. The MICA is one of 
four modules of PRISM (Processing Routines in 
IDL for Spectroscopic Measurements) which 
include: 1) ViewSPECPR; 2) spectral analysis 
routines; 3) image processing routines; and 4) 
MICA. MICA analyzes spectra by comparison to a 
spectral library and selects the best match to the 
entries in that library. The MICA process is 
illustrated in Figure 1 with a listing of the key 
inputs, analysis components, and outputs. The 
MICA command file contains the list of reference 
spectra and the analysis parameters used in 
conducting spectral comparisons.  
The shape of a reflectance spectrum derives, 
in large part, from the material’s chemical 
composition and physical structure [2]. Differences 
1569U.S. Government Work Not Protected by U.S. Copyright IGARSS 2011

<!-- page 2 -->

 
 
Fig. 1. Program flow and key algorithms of MICA module of PRISM. 
 
in these properties lead to differences in spectral 
shapes for minerals [2] and vegetation [3]. The 
central function of the MICA algorithm is spectral 
feature comparison applied to continuum removed 
absorption features. The continuum removed values 
of the spectrum being analyzed are compared to the 
values of the continuum removed reflectance feature 
in reference spectra of known composition by linear 
regression, where the wavelength region for the 
comparison is based on a diagnostic feature in the 
reference spectrum. Diagnostic features are strong 
and/or unique features arising from chemical bonds 
inherent in the reference material. The continuum 
removed values of the unknown and the reference 
are analyzed in linear regression. MICA uses the 
resultant coefficient of determination (r
2) as the “fit” 
value, that is, a measure of the agreement between 
the spectra. In contrast, Tetracorder uses the linear 
1570

<!-- page 3 -->

correlation coefficient (r) as the fit value [2]. The r2 
fit value ranges from 0 to 1, with better matches 
indicated by high fit numbers. To illustrate the 
spectral feature comparison of a single feature, a 
field spectrum measured in a rangeland ecosystem 
covered principally by dry grass (see fig. 2) is used 
as the spectrum of unknown composition and lab 
measurement of dry grass and dry pine as the 
reference spectra. The results show a higher fit to 
dry grass.
 
 
Fig. 2. Spectral comparison of a rangeland spectrum to spectral features of two reference materials.
 
1571

<!-- page 4 -->

MICA extends the spectral feature 
comparison concept to multiple features, allowing 
the user to define as many spectral features as 
desired for each reference spectrum listed in the 
command file and letting the user set the weighting 
factor for each feature. A single fit value, the 
“weighted fit”, is calculated by summing the 
products of the individual feature fits and their 
corresponding weighting factors. MICA arrives at an 
identification of the best match between the 
spectrum of an unknown material and the reference 
spectra in a MICA command file by selecting the 
material with the highest weighted fit value. Rather 
than relying solely on the fit values, MICA employs 
the concepts of feature and continuum constraints 
for each material in the command file in order to 
reduce false-positive identifications. In the command 
file, the user can define optional threshold values for 
each reference material for the minimum acceptable 
weighted fit value, allowable range of feature depth, 
fit*depth, reflectance levels at the midpoint and 
endpoints of the continuum line, and the ratio of the 
reflectance levels at the continuum endpoints. In 
order for its weighted fit value to be considered as 
the best match to the reference material, these values 
calculated from the spectrum being analyzed must 
meet any user-specified thresholds. To improve 
material identification, MICA employs the concept 
of NOT features. If any thresholds are violated or 
one or more of its listed NOT features are found, the 
weighted fit value for the material is zeroed out; that 
is, the material is removed from consideration as a 
match to the spectrum being analyzed. If all 
weighted fits to the reference spectra are zero, the 
MICA result indicates no match was made to the 
analyzed spectrum. MICA is used to analyze 
hyperspectral data, where the MICA analysis is 
performed on the spectrum in each pixel. 
The MICA command file is a user 
created/edited document listing the reference spectra 
and the spectral features to use in the analysis of 
spectra of unknown materials. A command file, 
containing reference spectra of 59 materials, was 
used to detect carbonates, phyllosilicates, sulfates, 
alteration-related minerals, and other materials 
absorbing in the 2 to 2.5 Pm region, in the full-
country coverage of HyMap data collected in 2007 
over Afghanistan. Mineral maps for Afghanistan 
have been derived from the MICA results. This 
command file will be released to the general public 
by the USGS, along with the PRISM/MICA 
software. 
 
3. REFERENCES 
[1] R.N. Clark, “SPECtrum Processing Routines 
User's Manual Version 3,” U.S. Geological Survey 
Open File Report 93-595, 210 p., 1993. 
 [2] R.N. Clark, G.A. Swayze, K.E. Livo, R.F. 
Kokaly, S.J. Sutley, J.B. Dalton, and others, 
“Imaging spectroscopy: Earth and planetary 
remote sensing with the USGS Tetracorder and 
expert systems,” Journal of Geophysical 
Research, vol. 108, p. 5131í5146, 2003. 
 [3] R.F. Kokaly, G.P. Asner, S.V. Ollinger, M.E. 
Martin, and C.A. Wessman, “Characterizing 
canopy biochemistry from imaging spectroscopy 
and its application to ecosystem studies,” Remote
Sensing of Environment, vol. 113, p. 78-91, 2009. 
1572