*!*********************************************************************
*!* export_ebill_standalone.prg
*!* 
*!* STANDALONE SCRIPT - No parameters needed
*!* 
*!* HOW TO RUN:
*!* 1. Open Visual FoxPro 9
*!* 2. Press Ctrl+O or File > Open
*!* 3. Navigate to: C:\Users\joche\source\repos\fwdcusifoxprocrystalreportstodevexpress\foxpro
*!* 4. Select this file (export_ebill_standalone.prg)
*!* 5. Press Ctrl+E or Program > Run
*!*********************************************************************

* Configuration - hardcoded paths
#DEFINE INPUT_FILE  "C:\Users\joche\source\repos\fwdcusifoxprocrystalreportstodevexpress\FoxPro_Ebill.frt"
#DEFINE OUTPUT_FILE "C:\Users\joche\source\repos\fwdcusifoxprocrystalreportstodevexpress\temp\FoxPro_Ebill.json"
#DEFINE TEMP_FOLDER "C:\Users\joche\source\repos\fwdcusifoxprocrystalreportstodevexpress\temp"

CLEAR
SET TALK OFF
SET SAFETY OFF
SET EXCLUSIVE OFF

LOCAL lcFrxFile, lcJsonFile, lcJson, lnRecNo, llFirst, lnControlCount, lnI
LOCAL lnObjType, lcExpr, lnHPos, lnVPos, lnWidth, lnHeight
LOCAL lcFontFace, lnFontSize, lnFontStyle

lcFrxFile = INPUT_FILE
lcJsonFile = OUTPUT_FILE

? "=============================================="
? "FoxPro FRT to JSON Export"
? "=============================================="
? "Input:  " + lcFrxFile
? "Output: " + lcJsonFile
?

* Create temp folder
IF NOT DIRECTORY(TEMP_FOLDER)
    MD (TEMP_FOLDER)
ENDIF

* Check if file exists
IF NOT FILE(lcFrxFile)
    ? "ERROR: File not found: " + lcFrxFile
    RETURN
ENDIF

* Open the FRT as a table
? "Opening FRT file..."

LOCAL llError
llError = .F.

TRY
    USE (lcFrxFile) ALIAS frxdata SHARED AGAIN NOUPDATE
CATCH TO loError
    ? "ERROR opening file: " + loError.Message
    llError = .T.
ENDTRY

IF llError
    RETURN
ENDIF

? "Record count: " + TRANSFORM(RECCOUNT())
? "Fields: " + TRANSFORM(FCOUNT())
?

* List field names
? "Field names:"
FOR lnI = 1 TO FCOUNT()
    ?? " " + FIELD(lnI)
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
lcJson = lcJson + '    "record_count": ' + TRANSFORM(RECCOUNT()) + CHR(13) + CHR(10)
lcJson = lcJson + '  },' + CHR(13) + CHR(10)

* Controls array
lcJson = lcJson + '  "controls": [' + CHR(13) + CHR(10)

GO TOP
llFirst = .T.
lnControlCount = 0

SCAN
    * Initialize defaults
    lnObjType = 0
    lcExpr = ""
    lnHPos = 0
    lnVPos = 0
    lnWidth = 0
    lnHeight = 0
    lcFontFace = "Arial"
    lnFontSize = 10
    lnFontStyle = 0
    
    * Read fields safely
    IF FIELD("OBJTYPE") # ""
        lnObjType = NVL(OBJTYPE, 0)
    ENDIF
    IF FIELD("EXPR") # ""
        lcExpr = NVL(ALLTRIM(EXPR), "")
    ENDIF
    IF FIELD("HPOS") # ""
        lnHPos = NVL(HPOS, 0)
    ENDIF
    IF FIELD("VPOS") # ""
        lnVPos = NVL(VPOS, 0)
    ENDIF
    IF FIELD("WIDTH") # ""
        lnWidth = NVL(WIDTH, 0)
    ENDIF
    IF FIELD("HEIGHT") # ""
        lnHeight = NVL(HEIGHT, 0)
    ENDIF
    IF FIELD("FONTFACE") # ""
        lcFontFace = NVL(ALLTRIM(FONTFACE), "Arial")
    ENDIF
    IF FIELD("FONTSIZE") # ""
        lnFontSize = NVL(FONTSIZE, 10)
    ENDIF
    IF FIELD("FONTSTYLE") # ""
        lnFontStyle = NVL(FONTSTYLE, 0)
    ENDIF
    
    * Export all records with expressions or known control types
    IF INLIST(lnObjType, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17) OR NOT EMPTY(lcExpr)
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

USE

? 
? "=============================================="
? "SUCCESS! Export complete!"
? "Controls exported: " + TRANSFORM(lnControlCount)
? "Output file: " + lcJsonFile
? "=============================================="
?
? "You can now close FoxPro and run the Python converter."

RETURN

*!*********************************************************************
FUNCTION EscJson
LPARAMETERS tcStr
    LOCAL lcResult
    IF EMPTY(tcStr)
        RETURN ""
    ENDIF
    lcResult = tcStr
    lcResult = STRTRAN(lcResult, "\", "\\")
    lcResult = STRTRAN(lcResult, '"', '\"')
    lcResult = STRTRAN(lcResult, CHR(13), "\r")
    lcResult = STRTRAN(lcResult, CHR(10), "\n")
    lcResult = STRTRAN(lcResult, CHR(9), "\t")
    RETURN lcResult
ENDFUNC
