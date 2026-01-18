*!*********************************************************************
*!* run_export.prg
*!* 
*!* Simple wrapper to run the export from VFP IDE
*!* Open VFP9, then: DO foxpro\run_export
*!*********************************************************************

SET TALK OFF
SET NOTIFY OFF  
SET SAFETY OFF

CLEAR

LOCAL lcFrxFile, lcJsonFile

* Set the paths here
lcFrxFile = "FoxPro_Ebill.frt"
lcJsonFile = "temp\FoxPro_Ebill.json"

* Create temp folder if needed
IF NOT DIRECTORY("temp")
    MKDIR temp
ENDIF

? "Running FoxPro Export..."
? "Input:  " + lcFrxFile
? "Output: " + lcJsonFile
?

* Run the export
DO foxpro\export_frt_to_json WITH lcFrxFile, lcJsonFile

? 
? "Done! Check " + lcJsonFile
