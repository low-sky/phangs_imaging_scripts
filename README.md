## README for PHANGS-ALMA Pipeline Version 2.0

### PREFACE

**Contents:** This is "version 2" of the PHANGS post-processing and science-ready data product pipeline. These programs use CASA, astropy, and affiliated packages (analysisutils, spectral-cube, reproject) to process data from the calibrated visibility to science-ready maps. The procedures and background for key parts of the pipeline are discussed in the Astrophysical Journal Supplements Paper "PHANGS-ALMA Data Processing and Pipeline" by Leroy, Hughes, Liu, Pety, Rosolowsky, Saito, Schinnerer, Usero, Faesi, Herrera et al.. Please consult that paper for more background and details.

**Pipeline and Configuration Files:** These are the programs to run the PHANGS-ALMA pipeline. Configuration files for a large set of PHANGS projects, including the live version of the files for the PHANGS-ALMA CO survey, exist in a separate repository. We include a frozen set of files that can be used to reduce PHANGS-ALMA as examples here. If you are need access to those other repositories or need examples, please request access as needed.

**Contact:** For issues, the preferred method is to open an issue on the github issues page. If you have specific other topics to discuss you can email the PHANGS-ALMA data reduction group at adr@phangs.groups.io . If you want to directly contact a person you can reach out to Adam Leroy, Erik Rosolowsky, or Daizhong Liu via email. But issues are better.

**Earlier Versions:** If you are looking for Version 1.0 of the pipeline, you can access it by changing branches to "version1.0". Note that this will mostly be for historical reasons. We suggest using Version 2.0 moving forward.

### WORKFLOW FOR MOST USERS

If you just want to *use* the pipeline then you will need to do three things:

( 0. Run scriptForPI to apply the observatory-provided calibration to your data. The pipeline picks up from there, it does not replace the outstanding ALMA observatory calibration and flagging pipeline. )

1. Make configuration files ("key files") that describe your project. Usually you can copy and modify an existing project to get a good start. We provide PHANGS-ALMA as an example.

2. Put together a small script to run the pipeline. Well, really put together two small scripts: one to runt he CASA stuff and another to run the pure python stuff. In theory these could be combined or generalized, but we usually just write a few small programs.

3. Run these scripts in order. The CASA stuff runs inside a CASA shell - the pipeline seems to work up through CASA 5.7 and has been heavily used in 5.4 and 5.6, In theory it should be workable in CASA 6.1+ but this isn't for sure yet. The pure python stuff expects a distribution with numpy, astropy, spectral-cube, and scipy and python 3.6+ or so.

**Procedure** A full pipeline run has four stages:

1. **Staging** Stage and process uv-data. This stage includes
continuum subtraction, line extraction, and regridding.

2. **Imaging** Image and deconvolve the uv-data. This runs in several
stages: dirty imaging, clean mask alignment, multi-scale
deconvolution, re-masking, and single convolution.

3. **Post-Process** Process deconvolved data into science-ready data
cubes. This stage includes merging with the total power and
mosaicking.

4. **Derive Produts** Convolution, noise estimation, masking, and
calculation of science-ready data products.

### CONTENTS OF THE PIPELINE IN MORE DETAIL

**Architecture** The pipeline is organized and run by a series of
"handler" objects. These handlers organize the list of targets, array
configurations, spectral products, and derived moments and execute
loops.

The routines to process individual data sets are in individual
modules, grouped by theme (e.g., casaImagingRoutines or
scNoiseRoutines). These routines do not know about the larger
infrastructure of arrays, targets, etc.. They generally take an input
file, output file, and various keyword arguments.

A project is defined by a series of text key files in a
"key_directory". These define the measurement set inputs,
configurations, spectral line products, moments, and derived
products. 

**User Control** For the most part the user's job is to *define the
key files* and to run some scripts.

