*!*********************************************************************
*!* export_frt_to_json.prg
*!* 
*!* Purpose: Exports FoxPro FRX/FRT report structure to JSON format
*!*          for conversion to DevExpress REPX using Python
*!*
*!* Usage:   DO export_frt_to_json WITH "myreport.frx", "output.json"
*!*          - OR -
*!*          vfp9.exe export_frt_to_json.prg myreport.frx output.json
*!*
*!* Author:  GitHub Copilot / Auto-generated
*!* Date:    2026-01-18
*!* Branch:  hybrid
*!*********************************************************************

LPARAMETERS tcFrxFile, tcJsonFile

* Handle command-line parameters
IF EMPTY(tcFrxFile)
    IF _VFP.StartMode > 0 AND PARAMETERS() < 2
        * Running from command line
        tcFrxFile = COMMAND(2)
        tcJsonFile = COMMAND(3)
    ENDIF
ENDIF

* Validate parameters
IF EMPTY(tcFrxFile)
    ? "Usage: DO export_frt_to_json WITH 'report.frx', 'output.json'"
    RETURN .F.
ENDIF

IF EMPTY(tcJsonFile)
    * Default output name
    tcJsonFile = FORCEEXT(tcFrxFile, "json")
ENDIF

IF NOT FILE(tcFrxFile)
    ? "Error: FRX file not found: " + tcFrxFile
    RETURN .F.
ENDIF

* =========================================================================
* MAIN EXPORT LOGIC
* =========================================================================

LOCAL lcJson, lcReportName, lnStartTime, lcFrxPath

lnStartTime = SECONDS()
lcFrxPath = FULLPATH(tcFrxFile)
lcReportName = JUSTSTEM(tcFrxFile)

? "Exporting: " + lcFrxPath
? "Output:    " + tcJsonFile

* Open the FRX as a table (read-only)
USE (tcFrxFile) ALIAS frxdata IN 0 SHARED AGAIN NOUPDATE

SELECT frxdata

* Build the main JSON structure
lcJson = '{' + CHR(13) + CHR(10)
lcJson = lcJson + '  "report": ' + GetReportInfo(lcReportName, lcFrxPath) + ',' + CHR(13) + CHR(10)
lcJson = lcJson + '  "page": ' + GetPageInfo() + ',' + CHR(13) + CHR(10)
lcJson = lcJson + '  "bands": ' + GetBands() + ',' + CHR(13) + CHR(10)
lcJson = lcJson + '  "controls": ' + GetControls() + CHR(13) + CHR(10)
lcJson = lcJson + '}'

* Write to file
STRTOFILE(lcJson, tcJsonFile)

USE IN frxdata

? "Export complete in " + TRANSFORM(SECONDS() - lnStartTime, "999.99") + " seconds"
? "Controls exported: " + TRANSFORM(gnControlCount)

RETURN .T.


*!*********************************************************************
*!* GetReportInfo - Returns report metadata as JSON
*!*********************************************************************
FUNCTION GetReportInfo(tcName, tcPath)
    LOCAL lcJson
    
    lcJson = '{' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "name": "' + EscapeJson(tcName) + '",' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "source_file": "' + EscapeJson(tcPath) + '",' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "exported_at": "' + TTOC(DATETIME(), 3) + '",' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "foxpro_version": "' + VERSION() + '"' + CHR(13) + CHR(10)
    lcJson = lcJson + '  }'
    
    RETURN lcJson
ENDFUNC


*!*********************************************************************
*!* GetPageInfo - Returns page setup from FRX record 1 (OBJTYPE=1)
*!*********************************************************************
FUNCTION GetPageInfo()
    LOCAL lcJson, lnWidth, lnHeight, lnLeft, lnTop, lnRight, lnBottom
    
    SELECT frxdata
    GO TOP
    
    * First record (OBJTYPE=1) contains page setup
    IF OBJTYPE = 1
        lnWidth = WIDTH
        lnHeight = HEIGHT
        lnLeft = HPOS
        lnTop = VPOS
    ELSE
        * Default letter size in FRUs (10000 per inch)
        lnWidth = 85000    && 8.5 inches
        lnHeight = 110000  && 11 inches
        lnLeft = 0
        lnTop = 0
    ENDIF
    
    lcJson = '{' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "width_fru": ' + TRANSFORM(lnWidth) + ',' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "height_fru": ' + TRANSFORM(lnHeight) + ',' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "left_margin_fru": ' + TRANSFORM(lnLeft) + ',' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "top_margin_fru": ' + TRANSFORM(lnTop) + ',' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "width_inches": ' + TRANSFORM(lnWidth / 10000, "999.99") + ',' + CHR(13) + CHR(10)
    lcJson = lcJson + '    "height_inches": ' + TRANSFORM(lnHeight / 10000, "999.99") + CHR(13) + CHR(10)
    lcJson = lcJson + '  }'
    
    RETURN lcJson
ENDFUNC


*!*********************************************************************
*!* GetBands - Returns all band definitions as JSON array
*!*********************************************************************
FUNCTION GetBands()
    LOCAL lcJson, lcBandType, lnBandCount, llFirst
    
    PUBLIC gaBands[1]
    lnBandCount = 0
    llFirst = .T.
    
    lcJson = '[' + CHR(13) + CHR(10)
    
    SELECT frxdata
    GO TOP
    
    SCAN
        * Band definition records
        IF INLIST(OBJTYPE, 0, 1, 2, 3, 4, 5, 6, 7, 8) AND EMPTY(EXPR)
            * Skip - these are band markers when OBJCODE is set
            lcBandType = GetBandTypeName(OBJTYPE)
            
            IF NOT EMPTY(lcBandType)
                IF NOT llFirst
                    lcJson = lcJson + ',' + CHR(13) + CHR(10)
                ENDIF
                llFirst = .F.
                
                lcJson = lcJson + '    {' + CHR(13) + CHR(10)
                lcJson = lcJson + '      "band_type": "' + lcBandType + '",' + CHR(13) + CHR(10)
                lcJson = lcJson + '      "objtype": ' + TRANSFORM(OBJTYPE) + ',' + CHR(13) + CHR(10)
                lcJson = lcJson + '      "objcode": ' + TRANSFORM(OBJCODE) + ',' + CHR(13) + CHR(10)
                lcJson = lcJson + '      "height_fru": ' + TRANSFORM(HEIGHT) + ',' + CHR(13) + CHR(10)
                lcJson = lcJson + '      "height_inches": ' + TRANSFORM(HEIGHT / 10000, "999.99") + CHR(13) + CHR(10)
                lcJson = lcJson + '    }'
                
                lnBandCount = lnBandCount + 1
            ENDIF
        ENDIF
    ENDSCAN
    
    lcJson = lcJson + CHR(13) + CHR(10) + '  ]'
    
    RETURN lcJson
ENDFUNC


*!*********************************************************************
*!* GetBandTypeName - Maps OBJTYPE/OBJCODE to band name
*!*********************************************************************
FUNCTION GetBandTypeName(tnObjType)
    LOCAL lcName
    
    DO CASE
        CASE tnObjType = 0 AND OBJCODE = 0
            lcName = "Title"
        CASE tnObjType = 1
            lcName = "Page Header"
        CASE tnObjType = 2
            lcName = "Column Header"
        CASE tnObjType = 3
            lcName = "Group Header"
        CASE tnObjType = 4
            lcName = "Detail"
        CASE tnObjType = 5
            lcName = "Group Footer"
        CASE tnObjType = 6
            lcName = "Column Footer"
        CASE tnObjType = 7
            lcName = "Page Footer"
        CASE tnObjType = 8
            lcName = "Summary"
        OTHERWISE
            lcName = ""
    ENDCASE
    
    RETURN lcName
ENDFUNC


*!*********************************************************************
*!* GetControls - Returns all controls (fields, labels, shapes) as JSON
*!*********************************************************************
FUNCTION GetControls()
    LOCAL lcJson, llFirst, lnRecNo
    
    PUBLIC gnControlCount
    gnControlCount = 0
    llFirst = .T.
    
    lcJson = '[' + CHR(13) + CHR(10)
    
    SELECT frxdata
    GO TOP
    
    SCAN
        * Control types: 5=Label, 6=Line, 7=Rectangle, 8=Field/Expression, 17=Picture
        IF INLIST(OBJTYPE, 5, 6, 7, 8, 17)
            IF NOT llFirst
                lcJson = lcJson + ',' + CHR(13) + CHR(10)
            ENDIF
            llFirst = .F.
            
            gnControlCount = gnControlCount + 1
            lnRecNo = RECNO()
            
            lcJson = lcJson + '    {' + CHR(13) + CHR(10)
            lcJson = lcJson + '      "id": ' + TRANSFORM(lnRecNo) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '      "objtype": ' + TRANSFORM(OBJTYPE) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '      "objtype_name": "' + GetObjTypeName(OBJTYPE) + '",' + CHR(13) + CHR(10)
            
            * Control name
            IF NOT EMPTY(NAME)
                lcJson = lcJson + '      "name": "' + EscapeJson(ALLTRIM(NAME)) + '",' + CHR(13) + CHR(10)
            ELSE
                lcJson = lcJson + '      "name": "Control' + TRANSFORM(lnRecNo) + '",' + CHR(13) + CHR(10)
            ENDIF
            
            * Position (in FRUs - 10000 per inch)
            lcJson = lcJson + '      "position": {' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "left_fru": ' + TRANSFORM(HPOS) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "top_fru": ' + TRANSFORM(VPOS) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "width_fru": ' + TRANSFORM(WIDTH) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "height_fru": ' + TRANSFORM(HEIGHT) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "left_inches": ' + TRANSFORM(HPOS / 10000, "999.9999") + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "top_inches": ' + TRANSFORM(VPOS / 10000, "999.9999") + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "width_inches": ' + TRANSFORM(WIDTH / 10000, "999.9999") + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "height_inches": ' + TRANSFORM(HEIGHT / 10000, "999.9999") + CHR(13) + CHR(10)
            lcJson = lcJson + '      },' + CHR(13) + CHR(10)
            
            * Expression/Content
            lcJson = lcJson + '      "expression": "' + EscapeJson(ALLTRIM(EXPR)) + '",' + CHR(13) + CHR(10)
            
            * Format/Picture
            lcJson = lcJson + '      "format": "' + EscapeJson(ALLTRIM(PICTURE)) + '",' + CHR(13) + CHR(10)
            
            * Font properties
            lcJson = lcJson + '      "font": {' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "name": "' + EscapeJson(ALLTRIM(FONTFACE)) + '",' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "size": ' + TRANSFORM(FONTSIZE) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "bold": ' + IIF(BITTEST(FONTSTYLE, 0), "true", "false") + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "italic": ' + IIF(BITTEST(FONTSTYLE, 1), "true", "false") + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "underline": ' + IIF(BITTEST(FONTSTYLE, 2), "true", "false") + CHR(13) + CHR(10)
            lcJson = lcJson + '      },' + CHR(13) + CHR(10)
            
            * Colors (RGB values)
            lcJson = lcJson + '      "colors": {' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "pen_rgb": [' + TRANSFORM(PENRED) + ',' + TRANSFORM(PENGREEN) + ',' + TRANSFORM(PENBLUE) + '],' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "fill_rgb": [' + TRANSFORM(FILLRED) + ',' + TRANSFORM(FILLGREEN) + ',' + TRANSFORM(FILLBLUE) + '],' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "pen_hex": "#' + RGB2Hex(PENRED, PENGREEN, PENBLUE) + '",' + CHR(13) + CHR(10)
            lcJson = lcJson + '        "fill_hex": "#' + RGB2Hex(FILLRED, FILLGREEN, FILLBLUE) + '"' + CHR(13) + CHR(10)
            lcJson = lcJson + '      },' + CHR(13) + CHR(10)
            
            * Alignment (0=Left, 1=Right, 2=Center)
            lcJson = lcJson + '      "alignment": ' + TRANSFORM(OFFSET) + ',' + CHR(13) + CHR(10)
            lcJson = lcJson + '      "alignment_name": "' + GetAlignmentName(OFFSET) + '",' + CHR(13) + CHR(10)
            
            * Print-when expression
            IF NOT EMPTY(SUPEXPR)
                lcJson = lcJson + '      "print_when": "' + EscapeJson(ALLTRIM(SUPEXPR)) + '",' + CHR(13) + CHR(10)
            ENDIF
            
            * Stretch mode
            lcJson = lcJson + '      "stretch": ' + IIF(STRETCH, "true", "false") + CHR(13) + CHR(10)
            
            lcJson = lcJson + '    }'
        ENDIF
    ENDSCAN
    
    lcJson = lcJson + CHR(13) + CHR(10) + '  ]'
    
    RETURN lcJson
ENDFUNC


*!*********************************************************************
*!* GetObjTypeName - Maps OBJTYPE code to name
*!*********************************************************************
FUNCTION GetObjTypeName(tnObjType)
    LOCAL lcName
    
    DO CASE
        CASE tnObjType = 5
            lcName = "Label"
        CASE tnObjType = 6
            lcName = "Line"
        CASE tnObjType = 7
            lcName = "Rectangle"
        CASE tnObjType = 8
            lcName = "Field"
        CASE tnObjType = 17
            lcName = "Picture"
        CASE tnObjType = 23
            lcName = "OLE"
        OTHERWISE
            lcName = "Unknown"
    ENDCASE
    
    RETURN lcName
ENDFUNC


*!*********************************************************************
*!* GetAlignmentName - Maps alignment code to name
*!*********************************************************************
FUNCTION GetAlignmentName(tnAlign)
    DO CASE
        CASE tnAlign = 0
            RETURN "Left"
        CASE tnAlign = 1
            RETURN "Right"
        CASE tnAlign = 2
            RETURN "Center"
        OTHERWISE
            RETURN "Left"
    ENDCASE
ENDFUNC


*!*********************************************************************
*!* RGB2Hex - Converts RGB values to hex string
*!*********************************************************************
FUNCTION RGB2Hex(tnR, tnG, tnB)
    RETURN PADL(TRANSFORM(tnR, "@0"), 2, "0") + ;
           PADL(TRANSFORM(tnG, "@0"), 2, "0") + ;
           PADL(TRANSFORM(tnB, "@0"), 2, "0")
ENDFUNC


*!*********************************************************************
*!* EscapeJson - Escapes special characters for JSON
*!*********************************************************************
FUNCTION EscapeJson(tcString)
    LOCAL lcResult
    
    IF EMPTY(tcString)
        RETURN ""
    ENDIF
    
    lcResult = tcString
    
    * Escape backslashes first
    lcResult = STRTRAN(lcResult, "\", "\\")
    * Escape quotes
    lcResult = STRTRAN(lcResult, '"', '\"')
    * Escape newlines
    lcResult = STRTRAN(lcResult, CHR(13), "\r")
    lcResult = STRTRAN(lcResult, CHR(10), "\n")
    * Escape tabs
    lcResult = STRTRAN(lcResult, CHR(9), "\t")
    
    RETURN lcResult
ENDFUNC
