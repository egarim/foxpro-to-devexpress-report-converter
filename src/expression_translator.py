"""
FoxPro to DevExpress Expression Translator

Maps FoxPro expressions to DevExpress Report expressions
"""

import re
from typing import Tuple, Optional, Dict, List


def normalize_field_name(name: str) -> str:
    """
    Normalize a field name for comparison across FoxPro and DevExpress.
    
    Examples:
        "PREVIOUS BALANCE" -> "previous_balance"
        "Previous Balance" -> "previous_balance"
        "prev_bal" -> "prev_bal"
        "SERVICE ADDRESS" -> "service_address"
    """
    # Remove quotes
    name = name.strip().strip('"\'')
    # Convert to lowercase
    name = name.lower()
    # Replace spaces and special chars with underscores
    name = re.sub(r'[\s\-]+', '_', name)
    # Remove non-alphanumeric except underscores
    name = re.sub(r'[^a-z0-9_]', '', name)
    return name


def match_field_names(pdf_fields: List[str], frt_fields: List[str]) -> Dict[str, str]:
    """
    Match PDF field names to FRT field names using fuzzy matching.
    
    Returns dict mapping PDF field name -> matched FRT field name
    """
    matches = {}
    
    # Normalize all FRT fields
    frt_normalized = {normalize_field_name(f): f for f in frt_fields}
    
    for pdf_field in pdf_fields:
        pdf_norm = normalize_field_name(pdf_field)
        
        # Exact match on normalized name
        if pdf_norm in frt_normalized:
            matches[pdf_field] = frt_normalized[pdf_norm]
            continue
        
        # Try partial matching
        for frt_norm, frt_orig in frt_normalized.items():
            # Check if one contains the other
            if pdf_norm in frt_norm or frt_norm in pdf_norm:
                matches[pdf_field] = frt_orig
                break
            # Check word overlap
            pdf_words = set(pdf_norm.split('_'))
            frt_words = set(frt_norm.split('_'))
            if len(pdf_words & frt_words) >= 1 and len(pdf_words) > 0:
                overlap_ratio = len(pdf_words & frt_words) / len(pdf_words)
                if overlap_ratio >= 0.5:
                    matches[pdf_field] = frt_orig
                    break
    
    return matches


class ExpressionTranslator:
    """
    Translates FoxPro expressions to DevExpress expression syntax
    """
    
    # FoxPro function to DevExpress function mapping
    FUNCTION_MAP = {
        # String functions
        'ALLTRIM': 'Trim',
        'LTRIM': 'TrimStart',
        'RTRIM': 'TrimEnd',
        'TRIM': 'Trim',
        'UPPER': 'Upper',
        'LOWER': 'Lower',
        'LEFT': 'Substring',  # LEFT(str, n) -> Substring([str], 0, n)
        'RIGHT': 'Right',  # Not direct, needs custom
        'SUBSTR': 'Substring',
        'LEN': 'Len',
        'STR': 'ToStr',
        'VAL': 'ToDecimal',
        'PADL': 'PadLeft',
        'PADR': 'PadRight',
        'PADC': 'PadLeft',  # Center padding approximation
        'STRTRAN': 'Replace',
        'STUFF': 'Insert',  # Approximation
        'REPLICATE': 'Replicate',
        'SPACE': 'PadLeft',  # Space(n) approximation
        
        # Date/Time functions
        'DATE': 'Today',
        'DATETIME': 'Now',
        'DTOC': 'FormatString',  # Date to character
        'CTOD': 'ToDateTime',
        'DTOS': 'FormatString',  # Date to string sortable
        'TTOC': 'FormatString',  # Time to character
        'YEAR': 'GetYear',
        'MONTH': 'GetMonth',
        'DAY': 'GetDay',
        'DOW': 'GetDayOfWeek',
        'HOUR': 'GetHour',
        'MINUTE': 'GetMinute',
        'SEC': 'GetSecond',
        'GOMONTH': 'AddMonths',
        'SHORTDATE': 'FormatString',  # Custom function
        
        # Numeric functions
        'ABS': 'Abs',
        'CEILING': 'Ceiling',
        'FLOOR': 'Floor',
        'ROUND': 'Round',
        'INT': 'Floor',
        'MOD': 'Modulo',  # a % b
        'MAX': 'Max',
        'MIN': 'Min',
        'SIGN': 'Sign',
        'SQRT': 'Sqrt',
        
        # Logical functions
        'IIF': 'Iif',
        'EMPTY': 'IsNullOrEmpty',
        'ISNULL': 'IsNull',
        'NVL': 'Iif',  # NVL(x, y) -> Iif(IsNull([x]), y, [x])
        'BETWEEN': 'Between',
        
        # Type conversion
        'TRANSFORM': 'FormatString',  # TRANSFORM(value, format)
        'CAST': 'ToStr',  # Simplified
    }
    
    # FoxPro format codes to .NET format codes
    FORMAT_MAP = {
        '$$$,$$$,$$$.##': '{0:C}',  # Currency
        '999,999,999.99': '{0:N2}',
        '99999999': '{0:D8}',
        '@D': '{0:d}',  # Short date
        '@YL': '{0:D}',  # Long date
        '@T': '{0:t}',  # Time
    }
    
    def __init__(self):
        self.field_mappings = {}  # Map FoxPro fields to DevExpress fields
        
    def translate(self, foxpro_expr: str) -> str:
        """
        Translate a FoxPro expression to DevExpress expression
        
        Args:
            foxpro_expr: FoxPro expression string
            
        Returns:
            DevExpress expression string
        """
        if not foxpro_expr:
            return ""
        
        expr = foxpro_expr.strip()
        
        # Handle string literals
        if expr.startswith('"') and expr.endswith('"'):
            return expr  # Keep as-is for DevExpress
        
        # Handle comma-separated string concatenation (FoxPro syntax)
        # alltrim(a),alltrim(b) -> Trim([a])+Trim([b])
        expr = self._translate_comma_concat(expr)
        
        # Handle simple field references
        if self._is_simple_field(expr):
            return self._translate_field(expr)
        
        # Translate complex expressions
        result = expr
        
        # Handle TRANSFORM function specially
        result = self._translate_transform(result)
        
        # Handle TRANS function (FoxPro shorthand/custom function)
        result = self._translate_trans(result)
        
        # Handle SHORTDATE function
        result = self._translate_shortdate(result)
        
        # Handle IIF function
        result = self._translate_iif(result)
        
        # Handle ALLTRIM and other string functions
        result = self._translate_string_functions(result)
        
        # Handle EMPTY function
        result = self._translate_empty(result)
        
        # Handle field references
        result = self._translate_field_references(result)
        
        # Handle operators
        result = self._translate_operators(result)
        
        # Convert double quotes to single quotes (DevExpress uses single quotes)
        result = self._convert_quotes(result)
        
        return result
    
    def _convert_quotes(self, expr: str) -> str:
        """
        Convert double-quoted strings to single-quoted strings.
        DevExpress uses single quotes for string literals.
        """
        # Replace "string" with 'string'
        # Handle escaped quotes inside
        result = []
        i = 0
        while i < len(expr):
            if expr[i] == '"':
                # Find the closing quote
                j = i + 1
                while j < len(expr):
                    if expr[j] == '"':
                        if j + 1 < len(expr) and expr[j+1] == '"':
                            # Escaped double quote
                            j += 2
                        else:
                            break
                    else:
                        j += 1
                # Extract the string content
                content = expr[i+1:j]
                # Convert escaped double quotes to escaped single quotes
                content = content.replace('""', "''")
                result.append("'")
                result.append(content)
                result.append("'")
                i = j + 1
            else:
                result.append(expr[i])
                i += 1
        return ''.join(result)
    
    def _translate_comma_concat(self, expr: str) -> str:
        """
        Translate FoxPro comma-based string concatenation.
        In FoxPro, commas outside of function arguments can act as string concat.
        Example: alltrim(a),alltrim(b) -> Trim([a])+Trim([b])
        """
        # First check if there are commas at the top level (outside parentheses)
        paren_depth = 0
        has_top_level_comma = False
        
        for c in expr:
            if c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
            elif c == ',' and paren_depth == 0:
                has_top_level_comma = True
                break
        
        if not has_top_level_comma:
            return expr
        
        # Split by top-level commas and join with +
        parts = []
        current = []
        paren_depth = 0
        
        for c in expr:
            if c == '(':
                paren_depth += 1
                current.append(c)
            elif c == ')':
                paren_depth -= 1
                current.append(c)
            elif c == ',' and paren_depth == 0:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(c)
        
        if current:
            parts.append(''.join(current).strip())
        
        # Join with + for DevExpress string concat
        return '+'.join(parts)
    
    def _is_simple_field(self, expr: str) -> bool:
        """Check if expression is a simple field reference"""
        # Simple field: alphanumeric with underscores, dots allowed for table.field
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$', expr))
    
    def _translate_field(self, field: str) -> str:
        """Translate a field reference to DevExpress format"""
        # FoxPro: table.field or just field
        # DevExpress: [Table.Field] or [Field]
        
        # Remove table prefix if it's a cursor/alias
        if '.' in field:
            parts = field.split('.')
            # Check if it's a known table alias to strip
            known_aliases = ['customer', 'service', 'cobilnotes']
            if parts[0].lower() in known_aliases:
                # Keep the capitalized field name
                field_name = parts[1].title()
                return f'[{field_name}]'
        
        # Convert to PascalCase for DevExpress
        pascal_field = ''.join(word.title() for word in field.split('_'))
        return f'[{pascal_field}]'
    
    def _translate_transform(self, expr: str) -> str:
        """
        Translate TRANSFORM function
        FoxPro: TRANSFORM(value, 'format')
        DevExpress: FormatString('{0:format}', [value])
        """
        pattern = r"TRANSFORM\s*\(\s*([^,]+)\s*,\s*'([^']+)'\s*\)"
        
        def replace(match):
            value = match.group(1).strip()
            format_code = match.group(2).strip()
            
            # Translate the value expression recursively
            dx_value = self.translate(value) if not self._is_simple_field(value) else self._translate_field(value)
            
            # Map FoxPro format to .NET format
            dx_format = self._map_format(format_code)
            
            return f"FormatString('{dx_format}', {dx_value})"
        
        return re.sub(pattern, replace, expr, flags=re.IGNORECASE)
    
    def _translate_trans(self, expr: str) -> str:
        """
        Translate TRANS function (FoxPro shorthand or custom function)
        FoxPro: TRANS(value) - converts to string for display
        DevExpress: ToStr([value])
        """
        pattern = r"\btrans\s*\(\s*([^)]+)\s*\)"
        
        def replace(match):
            field = match.group(1).strip()
            dx_field = self._translate_field(field) if self._is_simple_field(field) else self.translate(field)
            return f"ToStr({dx_field})"
        
        return re.sub(pattern, replace, expr, flags=re.IGNORECASE)
    
    def _translate_shortdate(self, expr: str) -> str:
        """
        Translate SHORTDATE function
        FoxPro: SHORTDATE(date_field)
        DevExpress: FormatString('{0:d}', [date_field])
        """
        pattern = r"SHORTDATE\s*\(\s*([^)]+)\s*\)"
        
        def replace(match):
            field = match.group(1).strip()
            dx_field = self._translate_field(field)
            return f"FormatString('{{0:d}}', {dx_field})"
        
        return re.sub(pattern, replace, expr, flags=re.IGNORECASE)
    
    def _translate_iif(self, expr: str) -> str:
        """
        Translate IIF function
        FoxPro: IIF(condition, true_value, false_value)
        DevExpress: Iif(condition, true_value, false_value)
        """
        # Simple case conversion
        return re.sub(r'\bIIF\s*\(', 'Iif(', expr, flags=re.IGNORECASE)
    
    def _translate_string_functions(self, expr: str) -> str:
        """Translate string functions"""
        result = expr
        
        # ALLTRIM -> Trim
        result = re.sub(r'\bALLTRIM\s*\(', 'Trim(', result, flags=re.IGNORECASE)
        
        # STR -> ToStr
        result = re.sub(r'\bSTR\s*\(', 'ToStr(', result, flags=re.IGNORECASE)
        
        # DTOC -> FormatString for date
        pattern = r"DTOC\s*\(\s*([^)]+)\s*\)"
        result = re.sub(pattern, r"FormatString('{0:d}', \1)", result, flags=re.IGNORECASE)
        
        # PADL -> PadLeft
        result = re.sub(r'\bPADL\s*\(', 'PadLeft(', result, flags=re.IGNORECASE)
        
        # STRTRAN -> Replace
        result = re.sub(r'\bSTRTRAN\s*\(', 'Replace(', result, flags=re.IGNORECASE)
        
        return result
    
    def _translate_empty(self, expr: str) -> str:
        """
        Translate EMPTY function
        FoxPro: EMPTY(field) or !EMPTY(field)
        DevExpress: IsNullOrEmpty([field]) or Not IsNullOrEmpty([field])
        """
        # Handle !EMPTY
        pattern = r"!EMPTY\s*\(\s*([^)]+)\s*\)"
        expr = re.sub(pattern, r"Not IsNullOrEmpty(\1)", expr, flags=re.IGNORECASE)
        
        # Handle EMPTY
        pattern = r"\bEMPTY\s*\(\s*([^)]+)\s*\)"
        expr = re.sub(pattern, r"IsNullOrEmpty(\1)", expr, flags=re.IGNORECASE)
        
        return expr
    
    def _translate_field_references(self, expr: str) -> str:
        """Translate field references in expression"""
        # Find field references like table.field or simple_field
        # and wrap them in brackets
        
        # Match table.field patterns
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\b'
        
        def replace(match):
            field = match.group(1)
            # Don't translate if already in brackets
            start = match.start()
            if start > 0 and expr[start-1] == '[':
                return field
            return self._translate_field(field)
        
        return re.sub(pattern, replace, expr)
    
    def _translate_operators(self, expr: str) -> str:
        """Translate FoxPro operators to DevExpress"""
        result = expr
        
        # Logical operators
        result = result.replace(' AND ', ' And ')
        result = result.replace(' OR ', ' Or ')
        result = result.replace(' NOT ', ' Not ')
        result = result.replace('.NOT.', ' Not ')
        result = result.replace('.AND.', ' And ')
        result = result.replace('.OR.', ' Or ')
        
        # Boolean literals
        result = result.replace('.T.', 'True')
        result = result.replace('.F.', 'False')
        result = result.replace('.NULL.', 'Null')
        
        # String concatenation (+ is same in DevExpress)
        
        # Not equal
        result = result.replace('#', ' <> ')
        result = result.replace('<>', ' <> ')
        result = result.replace('!=', ' <> ')
        
        return result
    
    def _map_format(self, foxpro_format: str) -> str:
        """Map FoxPro format code to .NET format code"""
        # Check if we have a direct mapping
        if foxpro_format in self.FORMAT_MAP:
            return self.FORMAT_MAP[foxpro_format]
        
        # Parse the format and convert
        # $$$,$$$,$$$.## -> Currency format
        if '$' in foxpro_format:
            return '{0:C}'
        
        # Count decimal places
        if '.' in foxpro_format:
            decimals = len(foxpro_format.split('.')[-1].replace('#', ''))
            return f'{{0:N{decimals}}}'
        
        # Default numeric
        return '{0:N}'


def test_translator():
    """Test the expression translator"""
    translator = ExpressionTranslator()
    
    test_cases = [
        # Simple fields
        ("acct_no", "[AcctNo]"),
        ("customer.address1", "[Address1]"),
        
        # String functions
        ("alltrim(acct_no)", "Trim([AcctNo])"),
        ("ALLTRIM(customer.CITY)+' '+alltrim(customer.STATE)", None),
        
        # TRANSFORM
        ("TRANSFORM(tot_cur,'$$$,$$$,$$$.##')", "FormatString('{0:C}', [TotCur])"),
        
        # Date functions
        ("SHORTDATE(billdate)", "FormatString('{0:d}', [Billdate])"),
        ("dtoc(due_date)", "FormatString('{0:d}', [DueDate])"),
        
        # IIF
        ("IIF(!empty(customer.spouse),alltrim(' & '+customer.spouse),'')", None),
        
        # EMPTY
        ("empty(customer.care_of)", "IsNullOrEmpty([CareOf])"),
        ("!empty(customer.address2)", "Not IsNullOrEmpty([Address2])"),
        
        # Boolean
        (".T.", "True"),
        (".F.", "False"),
        
        # Operators
        ("tot_chrg03#0.00", "[TotChrg03] <> 0.00"),
    ]
    
    print("Expression Translation Tests")
    print("=" * 60)
    
    for foxpro_expr, expected in test_cases:
        result = translator.translate(foxpro_expr)
        status = "✓" if expected is None or result == expected else "✗"
        print(f"\n{status} FoxPro: {foxpro_expr}")
        print(f"  Result: {result}")
        if expected:
            print(f"  Expected: {expected}")


if __name__ == "__main__":
    test_translator()
