*!*********************************************************************
*!* export_ebill.prg - Direct export script for FoxPro_Ebill.frt
*!* 
*!* Run from VFP command window:
*!*   CD C:\Users\joche\source\repos\fwdcusifoxprocrystalreportstodevexpress
*!*   DO foxpro\export_ebill
*!*********************************************************************

CLEAR
SET TALK OFF
SET SAFETY OFF

LOCAL lcFrxFile, lcJsonFile, lcJson, lnRecNo, llFirst

lcFrxFile = FULLPATH("FoxPro_Ebill.frt")
lcJsonFile = FULLPATH("temp\FoxPro_Ebill.json")

? "=============================================="
? "FoxPro FRT to JSON Export"
? "=============================================="
? "Input:  " + lcFrxFile
? "Output: " + lcJsonFile
?

* Create temp folder
IF NOT DIRECTORY("temp")
    MKDIR temp
ENDIF

* Check if file exists
IF NOT FILE(lcFrxFile)
    ? "ERROR: File not found: " + lcFrxFile
    RETURN
ENDIF

* Open the FRT as a table
? "Opening FRT file..."
USE (lcFrxFile) ALIAS frxdata IN 0 SHARED AGAIN NOUPDATE

? "Record count: " + TRANSFORM(RECCOUNT("frxdata"))
? "Fields: " + TRANSFORM(FCOUNT("frxdata"))
?

* List field names
? "Field names:"
FOR lnI = 1 TO FCOUNT("frxdata")
    ?? " " + FIELD(lnI, "frxdata")
ENDFOR
?
?

* Build JSON
? "Building JSON..."
lcJson = '{' + CHR(13) + CHR(10)
lcJson = lcJson + '  "report": {' + CHR(13) + CHR(10)
lcJson = lcJson + '    "name": "FoxPro_Ebill",' + CHR(13) + CHR(10)
lcJson = lcJson + '    "source_file": "' + STRTRAN(lcFrxFile, "\", "\\") + '",' + CHR(13) + CHR(10)
lcJson = lcJson + '    "exported_at": "' + TTOC(DATETIME(), 3) + '",' + CHR(13) + CHR(10)
lcJson = lcJson + '    "record_count": ' + TRANSFORM(RECCOUNT("frxdata")) + CHR(13) + CHR(10)
lcJson = lcJson + '  },' + CHR(13) + CHR(10)

* Controls array
lcJson = lcJson + '  "controls": [' + CHR(13) + CHR(10)

SELECT frxdata
GO TOP
llFirst = .T.
lnControlCount = 0

SCAN
    * Get OBJTYPE if it exists
    lnObjType = 0
    lcExpr = ""
    lnHPos = 0
    lnVPos = 0
    lnWidth = 0
    lnHeight = 0
    lcFontFace = "Arial"
    lnFontSize = 10
    lnFontStyle = 0
    
    * Try to read fields (they may not all exist)
    IF TYPE("frxdata.OBJTYPE") = "N"
        lnObjType = frxdata.OBJTYPE
    ENDIF
    IF TYPE("frxdata.EXPR") = "M" OR TYPE("frxdata.EXPR") = "C"
        lcExpr = ALLTRIM(frxdata.EXPR)
    ENDIF
    IF TYPE("frxdata.HPOS") = "N"
        lnHPos = frxdata.HPOS
    ENDIF
    IF TYPE("frxdata.VPOS") = "N"
        lnVPos = frxdata.VPOS
    ENDIF
    IF TYPE("frxdata.WIDTH") = "N"
        lnWidth = frxdata.WIDTH
    ENDIF
    IF TYPE("frxdata.HEIGHT") = "N"
        lnHeight = frxdata.HEIGHT
    ENDIF
    IF TYPE("frxdata.FONTFACE") = "C"
        lcFontFace = ALLTRIM(frxdata.FONTFACE)
    ENDIF
    IF TYPE("frxdata.FONTSIZE") = "N"
        lnFontSize = frxdata.FONTSIZE
    ENDIF
    IF TYPE("frxdata.FONTSTYLE") = "N"
        lnFontStyle = frxdata.FONTSTYLE
    ENDIF
    
    * Only export controls (objtype 5,6,7,8,17) or if we have expression
    IF INLIST(lnObjType, 5, 6, 7, 8, 17) OR NOT EMPTY(lcExpr)
        IF NOT llFirst
            lcJson = lcJson + ',' + CHR(13) + CHR(10)
        ENDIF
        llFirst = .F.
        lnControlCount = lnControlCount + 1
        
        lcJson = lcJson + '    {' + CHR(13) + CHR(10)
        lcJson = lcJson + '      "id": ' + TRANSFORM(RECNO()) + ',' + CHR(13) + CHR(10)
        lcJson = lcJson + '      "objtype": ' + TRANSFORM(lnObjType) + ',' + CHR(13) + CHR(10)
        lcJson = lcJson + '      "expression": "' + EscJson(lcExpr) + '",' + CHR(13) + CHR(10)
        lcJson = lcJson + '      "position": {' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "left_fru": ' + TRANSFORM(lnHPos) + ',' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "top_fru": ' + TRANSFORM(lnVPos) + ',' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "width_fru": ' + TRANSFORM(lnWidth) + ',' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "height_fru": ' + TRANSFORM(lnHeight) + CHR(13) + CHR(10)
        lcJson = lcJson + '      },' + CHR(13) + CHR(10)
        lcJson = lcJson + '      "font": {' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "name": "' + EscJson(lcFontFace) + '",' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "size": ' + TRANSFORM(lnFontSize) + ',' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "bold": ' + IIF(BITTEST(lnFontStyle, 0), "true", "false") + ',' + CHR(13) + CHR(10)
        lcJson = lcJson + '        "italic": ' + IIF(BITTEST(lnFontStyle, 1), "true", "false") + CHR(13) + CHR(10)
        lcJson = lcJson + '      }' + CHR(13) + CHR(10)
        lcJson = lcJson + '    }'
    ENDIF
ENDSCAN

lcJson = lcJson + CHR(13) + CHR(10) + '  ]' + CHR(13) + CHR(10)
lcJson = lcJson + '}'

* Write to file
? "Writing JSON file..."
STRTOFILE(lcJson, lcJsonFile)

USE IN frxdata

? 
? "=============================================="
? "Export complete!"
? "Controls exported: " + TRANSFORM(lnControlCount)
? "Output file: " + lcJsonFile
? "=============================================="

RETURN

*!*********************************************************************
FUNCTION EscJson(tcStr)
    LOCAL lcResult
    lcResult = tcStr
    lcResult = STRTRAN(lcResult, "\", "\\")
    lcResult = STRTRAN(lcResult, '"', '\"')
    lcResult = STRTRAN(lcResult, CHR(13), "\r")
    lcResult = STRTRAN(lcResult, CHR(10), "\n")
    lcResult = STRTRAN(lcResult, CHR(9), "\t")
    RETURN lcResult
ENDFUNC
