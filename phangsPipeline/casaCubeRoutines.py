"""
Standalone routines that take input and output files and manipulate
cubes. These are called as part of the PHANGS post-processing pipeline
but also may be of general utility.
"""

#region Imports and definitions

import os
import numpy as np
import pyfits # CASA has pyfits, not astropy
import glob

# Analysis utilities
import analysisUtils as au

# CASA stuff
import casaStuff as casa

# Pipeline versionining
from pipelineVersion import version as pipeVer

#endregion

#region FITS file manipulation, scaling, extraction, and unit handling

def copy_dropdeg(
    infile=None, 
    outfile=None, 
    overwrite=False,
    quiet=False):
    """
    Copy using imsubimage to drop degenerate axes. Optionally handle
    overwriting and importing from FITS.
    """

    this_stub = 'COPY_DROPDEG: '

    if os.path.isdir(outfile):
        if not overwrite:
            if not quiet:
                print(this_stub+"Output exists and overwrite set to false - "+outfile)
            return(False)
        os.system('rm -rf '+outfile)

    used_temp_outfile = False
    if (infile[-4:] == 'FITS') and os.path.isfile(infile):
        if not quiet:
            print(this_stub+"Importing from FITS.")
        temp_outfile = outfile+'.temp'
        if os.path.isdir(temp_outfile):
            if not overwrite:
                if not quiet:
                    print(this_stub+"Temp file exists and overwrite set to false - "+temp_outfile)
                return(False)
            os.system('rm -rf '+temp_outfile)
        
        importfits(fitsimage=infile, imagename=temp_outfile,
                   zeroblanks=True, overwrite=overwrite)
        used_temp_outfile = True

    if used_temp_outfile:
        casa.imsubimage(
            imagename=temp_outfile, 
            outfile=outfile,
            dropdeg=True)
        os.system('rm -rf '+temp_outfile)
    else:
        casa.imsubimage(
            imagename=infile, 
            outfile=outfile,
            dropdeg=True)
    
    return(True)

def primary_beam_correct(
    infile=None, 
    pbfile=None, 
    outfile=None, 
    cutoff=0.25, 
    overwrite=False,
    quiet=False):
    """
    Construct a primary-beam corrected image.
    """
    
    this_stub = 'PRIMARY_BEAM_CORRECT: '

    if infile is None or pbfile is None or outfile is None:
        if not quiet:
            print(this_stub+"Missing required input.")
        return(False)

    if os.path.isdir(infile) == False:
        if not quiet:
            print(this_stub+"Input file missing - "+infile)
        return(False)

    if os.path.isdir(pbfile) == False:
        if not quiet:
            print(this_stub+"Primary beam file missing - "+pbfile)
        return(False)

    if os.path.isfile(outfile) or os.path.isdir(outfile):
        if overwrite:
            os.system('rm -rf '+outfile)
        else:            
            if not quiet:
                print(this_stub+"Output exists and overwrite set to false - "+outfile)
            return(False)

    casa.impbcor(imagename=infile, pbimage=pbfile, outfile=outfile, cutoff=cutoff)

    return(True)
    
def convolve_to_round_beam(
    infile=None, 
    outfile=None, 
    force_beam=None, 
    overwrite=False,
    quiet=False):
    """
    Convolve supplied image to have a round beam. Optionally, force
    that beam to some size, else it figures out the beam.
    """
    
    this_stub = 'CONVOLVE_TO_ROUND_BEAM: '

    if infile is None or outfile is None:
        if not quiet:
            print(this_stub+"Missing required input.")
        return(None)

    if os.path.isdir(infile) == False:
        if not quiet:
            print(this_stub+"Input file missing - "+infile)
        return(None)

    if force_beam is None:
        hdr = casa.imhead(infile)

        if (hdr['axisunits'][0] != 'rad'):
            if not quiet:
                print(this_stub+"ERROR: Based on CASA experience. I expected units of radians.")
                print(this_stub+"I did not find this. Returning.")
                print(this_stub+"Adjust code or investigate file "+infile)
            return(None)
        pixel_as = abs(hdr['incr'][0]/np.pi*180.0*3600.)

        if (hdr['restoringbeam']['major']['unit'] != 'arcsec'):
            if not quiet:
                print(this_stub+"ERROR: Based on CASA experience. I expected units of arcseconds for the beam.")
                print(this_stub+"I did not find this. Returning.")
                print(this_stub+"Adjust code or investigate file "+infile)
            return(None)
        bmaj = hdr['restoringbeam']['major']['value']    
        target_bmaj = np.sqrt((bmaj)**2+(2.0*pixel_as)**2)
    else:
        target_bmaj = force_beam

    casa.imsmooth(imagename=infile,
                  outfile=outfile,
                  targetres=True,
                  major=str(target_bmaj)+'arcsec',
                  minor=str(target_bmaj)+'arcsec',
                  pa='0.0deg',
                  overwrite=overwrite
                  )

    return(target_bmaj)

def calc_jytok(
    hdr=None,
    infile=None,
    quiet=False):
    """
    Calculate the Jy/beam -> Kelvin conversion. Accepts a header
    already read using imhead or a file name that it will parse.
    """

    this_stub = 'CALC_JYTOK: '

    c = 2.99792458e10
    h = 6.6260755e-27
    kb = 1.380658e-16

    if hdr is None:
        if infile is None:
            if not quiet:                
                print(this_stub+"No header and no infile. Returning.")
            return(None)
        hdr = casa.imhead(target_file, mode='list')

    if hdr['cunit3'] != 'Hz':
        if not quiet:
            print(this_stub+"I expected frequency as the third axis but did not find it.")
            print(this_stub+"Returning.")
        return(None)
    
    crpix3 = hdr['crpix3']
    cdelt3 = hdr['cdelt3']
    crval3 = hdr['crval3']
    naxis3 = hdr['shape'][2]
    faxis_hz = (np.arange(naxis3)+1.-crpix3)*cdelt3+crval3
    freq_hz = np.mean(faxis_hz)
    
    bmaj_unit = hdr['beammajor']['unit']
    if bmaj_unit != 'arcsec':
        if not quiet:
            print(this_stub+"Beam unit is not arcsec, which I expected. Returning.")
            print(this_stub+"Unit instead is "+bmaj_unit)
        return(None)
    bmaj_as = hdr['beammajor']['value']
    bmin_as = hdr['beamminor']['value']
    bmaj_sr = bmaj_as/3600.*np.pi/180.
    bmin_sr = bmin_as/3600.*np.pi/180.
    beam_in_sr = np.pi*(bmaj_sr/2.0*bmin_sr/2.0)/np.log(2)
    
    jytok = c**2 / beam_in_sr / 1e23 / (2*kb*freq_hz**2)

    return(jytok)

def convert_jytok(
    infile=None, 
    outfile=None, 
    overwrite=False, 
    inplace=False,
    quiet=False):
    """
    Convert a cube from Jy/beam to K.
    """

    this_stub = 'CONVERT_JYTOK: '

    if infile is None or (outfile is None and inplace==False):
        if not quiet:
            print(this_stub+"Missing required input.")
        return(False)
    
    if os.path.isdir(infile) == False:
        if not quiet:
            print(this_stub+"Input file not found: "+infile)
        return(False)
    
    if inplace == False:
        if os.path.isdir(outfile) or os.path.isfile(outfile):
            if overwrite:
                os.system('rm -rf '+outfile)
            else:
                if not quiet:
                    print(this_stub+"Output file already present: "+outfile)
                return(False)

        os.system('cp -r '+infile+' '+outfile)
        target_file = outfile
    else:
        target_file = infile

    hdr = casa.imhead(target_file, mode='list')
    unit = hdr['bunit']
    if unit != 'Jy/beam':
        if not quiet:
            print(this_stub+"Input unit is not Jy/beam for file "+target_file)
            print(this_stub+"Instead found "+unit)
        return(False)
    
    jytok = calc_jytok(hdr=hdr)

    myia = au.createCasaTool(iatool)
    myia.open(target_file)
    vals = myia.getchunk()
    vals *= jytok
    myia.putchunk(vals)
    myia.setbrightnessunit("K")
    myia.close()

    casa.imhead(target_file, mode='put', hdkey='JYTOK', hdvalue=jytok)

    return(True)

def convert_ktojy(
    infile=None, 
    outfile=None, 
    overwrite=False, 
    inplace=False,
    quiet=False):
    """
    Convert a cube from K to Jy/beam.
    """

    this_stub = 'CONVERT_KTOJY: '

    if infile is None or (outfile is None and inplace==False):
        if not quiet:
            print(this_stub+"Missing required input.")
        return(False)
    
    if os.path.isdir(infile) == False:
        if not quiet:
            print(this_stub+"Input file not found: "+infile)
        return(False)
    
    if inplace == False:
        if os.path.isdir(outfile) or os.path.isfile(outfile):
            if overwrite:
                os.system('rm -rf '+outfile)
            else:
                if not quiet:
                    print(this_stub+"Output file already present: "+outfile)
                return(False)

        os.system('cp -r '+infile+' '+outfile)
        target_file = outfile
    else:
        target_file = infile

    hdr = casa.imhead(target_file, mode='list')
    unit = hdr['bunit']
    if unit != 'K':
        if not quiet:
            print(this_stub+"Input unit is not K for file "+target_file)
            print(this_stub+"Instead found "+unit)
        return(False)
    
    jytok = calc_jytok(hdr=hdr)

    myia = au.createCasaTool(iatool)
    myia.open(target_file)
    vals = myia.getchunk()
    vals *= 1.0/jytok
    myia.putchunk(vals)
    myia.setbrightnessunit("Jy/beam")
    myia.close()

    casa.imhead(target_file, mode='put', hdkey='JYTOK', hdvalue=jytok)

    return(True)

def trim_cube(    
    infile=None, 
    outfile=None, 
    overwrite=False, 
    inplace=False, 
    min_pixperbeam=3,
    quiet=False):
    """
    Trim empty space from around the edge of a cube. Also rebin the
    cube to smaller size, while ensuring a minimum number of pixels
    across the beam. Used to reduce the volume of cubes.
    """
    
    this_stub = 'TRIM_CUBE: '

    if infile is None or outfile is None:
        if not quiet:
            print(this_stub+"Missing required input.")
        return(False)
    
    if os.path.isdir(infile) == False:
        if not quiet:
            print(this_stub+"Input file not found: "+infile)
        return(False)

    # First, rebin if needed
    hdr = casa.imhead(infile)
    if (hdr['axisunits'][0] != 'rad'):
        if not quiet:
            print(this_stub+"ERROR: Based on CASA experience. I expected units of radians.")
            print(this_stub+"I did not find this. Returning.")
            print(this_stub+"Adjust code or investigate file "+infile)
        return(False)

    pixel_as = abs(hdr['incr'][0]/np.pi*180.0*3600.)

    if (hdr['restoringbeam']['major']['unit'] != 'arcsec'):
        if not quiet:
            print(this_stub+"ERROR: Based on CASA experience. I expected units of arcseconds for the beam.")
            print(this_stub+"I did not find this. Returning.")
            print(this_stub+"Adjust code or investigate file "+infile)
        return(False)
    bmaj = hdr['restoringbeam']['major']['value']    
    
    pix_per_beam = bmaj*1.0 / pixel_as*1.0
    
    if pix_per_beam > 6:
        casa.imrebin(
            imagename=infile,
            outfile=outfile+'.temp',
            factor=[2,2,1],
            crop=True,
            dropdeg=True,
            overwrite=overwrite,
            )
    else:
        os.system('cp -r '+infile+' '+outfile+'.temp')

    # Figure out the extent of the image inside the cube
    myia = au.createCasaTool(iatool)
    myia.open(outfile+'.temp')
    mask = myia.getchunk(getmask=True)    
    myia.close()

    this_shape = mask.shape

    mask_spec_x = np.sum(np.sum(mask*1.0,axis=2),axis=1) > 0
    pad = 0
    xmin = np.max([0,np.min(np.where(mask_spec_x))-pad])
    xmax = np.min([np.max(np.where(mask_spec_x))+pad,mask.shape[0]-1])

    mask_spec_y = np.sum(np.sum(mask*1.0,axis=2),axis=0) > 0
    ymin = np.max([0,np.min(np.where(mask_spec_y))-pad])
    ymax = np.min([np.max(np.where(mask_spec_y))+pad,mask.shape[1]-1])

    mask_spec_z = np.sum(np.sum(mask*1.0,axis=0),axis=0) > 0
    zmin = np.max([0,np.min(np.where(mask_spec_z))-pad])
    zmax = np.min([np.max(np.where(mask_spec_z))+pad,mask.shape[2]-1])
    
    box_string = ''+str(xmin)+','+str(ymin)+','+str(xmax)+','+str(ymax)
    chan_string = ''+str(zmin)+'~'+str(zmax)

    if not quiet:
        print(this_stub+"... box selection: "+box_string)
        print(this_stub+"... channel selection: "+chan_string)

    if overwrite:
        os.system('rm -rf '+outfile)
        casa.imsubimage(
            imagename=outfile+'.temp',
            outfile=outfile,
            box=box_string,
            chans=chan_string,
            )
    
    os.system('rm -rf '+outfile+'.temp')

    return(True)
    
def export_and_cleanup(
    infile=None,
    outfile=None,
    overwrite=False,    
    remove_cards=[],
    add_cards=[],
    add_history=[],
    zap_history=True,
    roundbeam_tol=0.01,
    quiet=False):
    """
    Export from a CASA image file to a FITS file, in the process
    cleaning up header keywords that are usually confusing or
    useless. Optionally add new keywords to the header and check
    whether the beam is close enough to being round that it makes
    sense to overwrite it.
    """
    
    this_stub = 'EXPORT_AND_CLEANUP: '

    if infile is None or outfile is None:
        if not quiet:
            print(this_stub+"Missing required input.")
        return(False)

    if os.path.isfile(outfile):
        if not overwrite:
            if not quiet:
                print(this_stub+"Output exists and overwrite set to false - "+outfile)
            return(False)

    casa.exportfits(imagename=infile, 
                    fitsimage=outfile,
                    velocity=True, overwrite=True, dropstokes=True, 
                    dropdeg=True, bitpix=-32)
    
    # Clean up headers

    hdu = pyfits.open(outfile)

    hdr = hdu[0].header
    data = hdu[0].data
    
    # Cards to remove by default

    for card in ['BLANK','DATE-OBS','OBSERVER','O_BLANK','O_BSCALE',
                 'O_BZERO','OBSRA','OBSDEC','OBSGEO-X','OBSGEO-Y','OBSGEO-Z',
                 'DISTANCE']:
        if card in hdr.keys():
            hdr.remove(card)
            
    # User cards to remove

    for card in remove_cards:
        if card in hdr.keys():
            hdr.remove(card)
            
    # Delete history
    
    if zap_history:
        while 'HISTORY' in hdr.keys():
            hdr.remove('HISTORY')

    # Add history

    for history_line in add_history:
        add_history(history_line)
            
    # Get the data min and max right

    datamax = np.nanmax(data)
    datamin = np.nanmin(data)
    hdr['DATAMAX'] = datamax
    hdr['DATAMIN'] = datamin

    # Round the beam recorded in the header if it lies within the
    # specified tolerance.

    if roundbeam_tol > 0.0:
        bmaj = hdr['BMAJ']
        bmin = hdr['BMIN']
        if bmaj != bmin:
            frac_dev = np.abs(bmaj-bmin)/bmaj
            if frac_dev <= roundbeam_tol:
                print("Rounding beam.")
                hdr['BMAJ'] = bmaj
                hdr['BMIN'] = bmaj
                hdr['BPA'] = 0.0
            else:
                print(this_stub+"Beam too asymmetric to round.")
                print(this_stub+"... fractional deviation: "+str(frac_dev))
    
    # Overwrite

    hdu.writeto(outfile, clobber=True)
        
    return()

#endregion
