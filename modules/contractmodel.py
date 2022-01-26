import os
import re
import requests
import pprint
import validators
import pandas as pd
from solidity_parser import parser

if not os.path.isdir('/tmp'):
    os.mkdir('/tmp')

ERRORMSG = 'error: could not parse'
IGNORE_CONTRACTS = ['SafeMath']

# =============================================================================
# Define data model based on solidity_parser AST
# =============================================================================
class ContractObject():
    SUPPORTED_OBJECTS = ['ContractDefinition', 'EventDefinition', 'ModifierDefinition', 'FunctionDefinition', 'StructDefinition', 'EnumDefinition']
    
    def __init__(self, ast_item, contractName):
        """Initialize object given portion of AST tree"""
        
        self.contract = contractName
        self.type = ast_item['type']
        
        assert self.type in self.SUPPORTED_OBJECTS, ""#f"Warning: {self.type} type in {contractName} is not supported by ContractObject"
        
        if self.type == 'ContractDefinition':
            self.objectName = contractName
            self.inheritance = [b['baseName']['namePath'] for b in ast_item.get('baseContracts', [])]
            self.modifiers = ''
            self.values = ''
            self.visibility = ''
        else:
            name = ast_item['name']
            if name.startswith('function()'):
                # Nameless delegator functions are not parsed correctly by solidity_parser
                name = '(none)'
            self.objectName = name
            self.inheritance = ''
            self.modifiers = self.get_object_modifiers(ast_item)
            self.values = self.get_object_values(ast_item)
            self.visibility = ast_item.get('visibility', '')
            
        self.lineNumbers = (ast_item['loc']['start']['line'], ast_item['loc']['end']['line'])
                
        self.description = ''
        
    def as_Series(self):
        """Return variables as pd.Series"""
        
        objDict = {'object_name': self.objectName, 
                   'contract': self.contract, 
                   'type': self.type, 
                   'inheritance': self.inheritance, 
                   'modifiers': self.modifiers, 
                   'values': self.values, 
                   'visibility': self.visibility, 
                   'line_numbers': self.lineNumbers, 
                   'description': self.description
                  }
        return pd.Series(objDict)
    
    def get_object_modifiers(self, obj):
        """Get object modifiers"""

        modifiers = obj.get('modifiers', [])
        modifiers = [m.get('name', ERRORMSG) for m in modifiers]

        return modifiers

    def get_object_values(self, obj):
        """Get object options ("members" as defined in enum objects only)"""

        values = []

        if obj['type'] == 'EnumDefinition':
            members = obj.get('members', [])
            values = [m.get('name', ERRORMSG) for m in members]

        return values
    

class ContractParameter():
    def __init__(self, ast_item, parentObject):
        """Initialize parameter given portion of AST tree"""
        
        self.parameterName = ast_item['name']
        self.parentObject = parentObject

        self.lineNumber = ast_item['loc']['start']['line']
        self.visibility = ast_item.get('visibility', '')        
        
        self.type = self.get_parameter_type(ast_item)
        self.typeCategory = self.get_parameter_type_category(ast_item)
        self.initialValue = self.get_parameter_initialValue(ast_item)
        
        self.description = ''
        
    def as_Series(self):
        """Return variables as pd.Series"""
        
        paramDict = {'parameter_name': self.parameterName, 
                     'object_name': self.parentObject.objectName, 
                     'contract': self.parentObject.contract, 
                     'type': self.type, 
                     'type_category': self.typeCategory, 
                     'line_number': self.lineNumber, 
                     'initial_value': self.initialValue, 
                     'visibility': self.visibility, 
                     'description': self.description
                    }
        return pd.Series(paramDict)
    
    def get_parameter_type(self, param):
        """Get parameter data type"""

        typeDict = param['typeName']
        typeType = typeDict.get('type')

        if typeType == 'Mapping':
            # Really should be something recursive to handle cases like `mapping (key => type:Mapping)`
            kType = typeDict['keyType']
            vType = typeDict['valueType']
            k = kType.get('name', kType.get('namePath', 'type:' + kType.get('type', '?')))
            v = vType.get('name', vType.get('namePath', 'type:' + vType.get('type', '?')))
            paramType = f"mapping ({k} => {v})" 
        elif typeType == 'ArrayTypeName':
            # Really should be something recursive to handle cases like `type:UserDefinedType[] memory`
            bType = typeDict.get('baseTypeName', {})
            baseType = bType.get('name', bType.get('namePath', 'type:' + bType.get('type', '?')))
            location = param.get('storageLocation', None)
            if location is None:
                location = ''
            length = typeDict.get('length', None)
            if length is None:
                length = ''
            paramType = f"{baseType}[{length}] {location}".strip()
        else:
            paramType = typeDict.get('name', typeDict.get('namePath', ERRORMSG))

        return paramType
    
    def get_parameter_initialValue(self, param):
        """Get parameter initialValue"""

        value = param.get('initialValue')
        if value is not None:
            value = value.get('value', str(value))

        return value
    
    def get_parameter_type_category(self, param):
        """Get category of parameter dtype
        
        If ElementaryTypeName: returns the type stripped of any specific size indication (e.g., 'uint8' --> 'uint')
        If Mapping: returns 'map'
        If ArrayTypeName or UserDefinedTypeName: returns 'array' or 'userdefined'
        """

        typeDict = param['typeName']
        typeType = typeDict.get('type')
        if 'TypeName' in typeType and not 'Elementary' in typeType:
            paramCategory = typeType[:-8].lower()
        elif typeType == 'Mapping':
            paramCategory = 'map'
        else:
            paramCategory = typeDict.get('name', typeDict.get('namePath', ERRORMSG))

        # Strip digits from (end of) string (to remove size spcification from bytes, int, uint8)
        paramCategory = re.sub(r"\d+", "", paramCategory)

        return paramCategory
    

# =============================================================================
# Populate data model based on solidity_parser AST
# =============================================================================    
def extract_objects_and_parameters(sourceUnit):
    """Collect information on contract objects and their parameters
    
    Input: solidity-parser parsed AST for the contract file
    
    Returns two DataFrames:
      - df_objects contains contracts, function, event, modifier, struct, and enum definitions
      - df_parameters contains state variables, function arguments, struct values, and other
        parameters needed to define or call the above
        
    Each contract/parameter is first defined using the ContractObject or ContractParameter class
    to pull the relevant information from the AST node, then exported to a Series for storage in
    the corresponding DataFrame.
    """
    
    # Get list of relevant contract nodes defined in Solidity file
    contracts = [c for c in sourceUnit['children'] if c.get('type') == 'ContractDefinition']
    contracts = [c for c in contracts if c['name'] not in IGNORE_CONTRACTS]
    
    df_objects = pd.DataFrame()
    df_parameters = pd.DataFrame()
    
    # Iterate through contracts to extract objects and their parameters
    for c in contracts:
        contractName = c['name']
    
        # Append object for the contract itself
        contract = ContractObject(c, contractName)
        df_objects = df_objects.append(contract.as_Series(), ignore_index=True)

        # Iterate through relevant subnodes in contract
        for item in c.get('subNodes', []):
            itemType = item['type']
            
            if itemType == 'StateVariableDeclaration':
                # Append contract state variables to parameters DataFrame
                for param in item.get('variables', {}):
                    stateVar = ContractParameter(param, contract)
                    df_parameters = df_parameters.append(stateVar.as_Series(), ignore_index=True)
            else:
                try: 
                    # Append function/event/modifier definition to objects DataFrame
                    contractObj = ContractObject(item, contractName)
                    df_objects = df_objects.append(contractObj.as_Series(), ignore_index=True)

                    # Append each parameter to DataFrame
                    paramObj = item.get('parameters', (item.get('members', {})))
                    if isinstance(paramObj, dict):
                        values = paramObj.get('parameters', [])
                    elif isinstance(paramObj, list) and itemType == 'StructDefinition':
                        values = paramObj
                    else:
                        values = []
                    for param in values:
                        contractParam = ContractParameter(param, contractObj)
                        df_parameters = df_parameters.append(contractParam.as_Series(), ignore_index=True)
                except AssertionError as e:
                    # If unsupported object type is encountered
                    print(e)

    return df_objects, df_parameters


# =============================================================================
# Populate object and parameter comments
# =============================================================================
def _clean_comment_lines(lines):
    """Clean list of strings that may contain a block comment or contiguous set of
    individual line comments.
    
    Assumes that, if the list contains multiple such blocks/sets, the only relevant one
    is the one at the end of the list (immediately prior to e.g., the object definition).
    
    Arguments:
    - lines (list(str)): list of lines that may contain comments
    Returns:
    - lines_new (list(str)): cleaned list of comments (may be empty list)
    """
    
    lines = [s.strip() for s in lines if s.strip()]
    linesStr = '\n'.join(lines)
    
    # Try to get comment block right before the object, if there is one
    pattern_commentBlock = re.compile(r'/\*\*(.+?)\*/$', re.DOTALL)
    match = re.search(pattern_commentBlock, linesStr)
    if match:
        # Remove asterisks
        lines_new = match.group(1).split('\n')
        lines_new = [re.sub('^\s*\*\s*', '', s).strip() for s in lines_new if s]
    else:
        # Otherwise, get contiguous block of individual line comments right before object
        lines_new = []
        i = len(lines) - 1
        endFlag = False
        while i >= 0 and not endFlag:
            if lines[i].startswith('//'):
                lines_new.append(re.sub(r'//+', '', lines[i]).strip())
            else:
                endFlag = True
            i -= 1
        lines_new = lines_new[::-1]
    
    return lines_new


def clean_comment_lines(lines_raw, includesInline=False):
    """Clean list of strings of up to (and including, if includesInline=True)
    an object or parameter definition
    
    Arguments:
      - lines_raw (list(str)): list of lines that may contain comments
      - includesInline (bool): whether the last entry in the list should be
        parsed as an inline comment
    Returns:
      - lines_new (list(str)): cleaned list of comments (may be empty list)
    """
    
    if includesInline:
        # Clean comment lines prior to inline
        prevLines = _clean_comment_lines(lines_raw[:-1])
        
        # Clean inline comment separately and add to prior comments
        tmp = re.split(r'//+', lines_raw[-1])
        inLine = [tmp[-1]] if len(tmp) > 1 else ['']
        lines_new = prevLines + inLine
    else:
        lines_new = _clean_comment_lines(lines_raw)
    
    lines_new = [s.strip() for s in lines_new if s.strip()]
    
    return lines_new


def parse_object_comments(lines_raw):
    """Clean and parse list of lines prior to an object definition.
    May contain a block comment or individual line comments. If it contains 
    unrelated lines of code, these will be filtered out.
    Tries to find NatSpec tags, if any; either way, keeps full comment and sets
    a one-line description.
        
    Arguments:
      - lines_raw (list(str)): list of lines that may contain relevant comments
    Returns:
      - commentDict (dict): contains the following:
          - tag:value items for any NatSpec tags used. For 'param', value is
            dict of param:description items
          - 'full_comment' and 'description' keys for full (cleaned) comment
            string and one-line description
    """

    commentDict = {}    
    
    # Clean lines
    lines = clean_comment_lines(lines_raw)  
    
    # Don't bother with the rest if no description was found
    if len(lines) == 0:
        return commentDict

    # Add full (cleaned) comment
    commentDict['full_comment'] = '\n'.join(lines)  
    
    # Add tag values, if NatSpec is used
    splitLines = re.split(r'\n@([a-z]+)', '\n' + '\n'.join(lines))[1:] 
    if len(splitLines) > 0:
        values = zip(splitLines[::2], splitLines[1::2])
        for (tag, value) in values:
            prevValue = commentDict.get(tag, '')
            if not prevValue:
                commentDict[tag] = value.replace('\n', ' ').strip()
            else:
                commentDict[tag] = prevValue + '\n' + value.replace('\n', ' ').strip()
    
    # Split parameters (if any) into a dictionary
    params = commentDict.get('param', '')
    if params:
        paramLines = [s.split(' ', 1) for s in params.split('\n')]
        commentDict['param'] = {p[0]: p[1] for p in paramLines}
    
    # Control flow for choosing main description
    if 'title' in commentDict.keys():
        description = commentDict['title']
    elif 'notice' in commentDict.keys():
        description = commentDict['notice']
    elif 'dev' in commentDict.keys():
        description = commentDict['dev']
    elif 'return' in commentDict.keys():
        description = commentDict['return']
    else:
        description = commentDict['full_comment'].split('.')[0]
    commentDict['description'] = description
    
    return commentDict


def parse_parameter_comments(lines_raw):
    """Clean and parse list of lines up to and including a parameter definition.
    May contain a block comment or individual line comments. If it contains 
    unrelated lines of code, these will be filtered out.
        
    Arguments:
      - lines_raw (list(str)): list of lines that may contain relevant comments
    Returns:
      - commentDict (dict): contains the following:
          - 'full_comment' and 'description' keys for full (cleaned) comment
            string and one-line description
    """

    # Clean lines
    lines = clean_comment_lines(lines_raw, includesInline=True)
    
    commentDict = {}

    # Don't bother with the rest if no description was found
    if len(lines) == 0:
        return commentDict    
   
    # Add full (cleaned) comment
    commentDict['full_comment'] = '\n'.join(lines)      

    # Strip any tags from the description
    lines_noTags = [re.split(r'@[a-z]+', s)[-1].strip() for s in lines]
    
    # Add description
    hasInline = (lines[-1] in lines_raw[-1])
    if hasInline and len(lines) == 1:
        inline = lines[0]
        description = inline
    elif hasInline:
        description = ' '.join(lines_noTags[:-1])
        inline = lines_noTags[-1]
    else:
        description = ' '.join(lines_noTags)
        inline = ''
    commentDict['description'] = description
    commentDict['inline_comment'] = inline
    
    return commentDict


def add_docstring_comments(lines, df_objects, df_parameters):
    """Parse comments and add them to the relevant rows in the object and parameter DataFrames"""

    df_o = df_objects.copy(deep=True)
    df_p = df_parameters.copy(deep=True)

    # Define tags to keep
    NATSPEC_TAGS = ['title', 'notice', 'dev', 'param', 'return']
    for tag in NATSPEC_TAGS:
        df_o[tag] = ''
    df_o['description'] = ''
    df_o['full_comment'] = ''
        
    prevObjectLoc = (0,0)
    for i, row in df_o.iterrows():
        # Get, clean, and parse object comment lines
        commentEnd = row['line_numbers'][0] - 1
        if prevObjectLoc[1] <= commentEnd:
            commentStart = prevObjectLoc[1]
        else:
            commentStart = prevObjectLoc[0]
        commentLines = lines[commentStart:commentEnd]
        commentDict = parse_object_comments(commentLines)

        # Add object descriptions to objects
        for key, value in commentDict.items():
            if key in df_o.columns:
                if key == 'param':
                    value = list(value.keys())
                df_o.iat[i, df_o.columns.get_loc(key)] = value               

        # Add parameter descriptions to parameters
        for paramName, paramDescription in commentDict.get('param', {}).items():
            index = df_p.loc[(df_p['object_name']==row['object_name']) &
                             (df_p['parameter_name']==paramName)].index[0]
            df_p.iat[index, df_p.columns.get_loc('description')] = paramDescription

        prevObjectLoc = row['line_numbers']

    return df_o, df_p


def add_inline_comments(lines, df_parameters):
    """Parse comments and add them to the relevant rows in the parameter DataFrame"""

    df_p = df_parameters.copy(deep=True)
    df_p['full_comment'] = ''

    commentStart = 0
    for i, row in df_p.iterrows():   
        # Grab and parse comment lines
        commentEnd = int(row['line_number'])
        commentLines = lines[min(commentStart, commentEnd - 2):commentEnd]
        commentDict = parse_parameter_comments(commentLines)
        
        # Add to dict (but don't overwrite previously found value)
        for key, value in commentDict.items():
            if key in df_p.columns:
                currentValue = df_p.iat[i, df_p.columns.get_loc(key)]
                if not currentValue:
                    df_p.iat[i, df_p.columns.get_loc(key)] = value

        commentStart = commentEnd

    return df_p


def remove_duplicate_comments_in_parameters(df_o, df_parameters):
    """Remove description and/or full comment for a parameter if it is 
    the same as its parent object's description"""
    
    df_p = df_parameters.copy(deep=True)
    
    for i, row in df_parameters.iterrows():
        # Get parent object's comments
        index = df_o.loc[(df_o['object_name']==row['object_name']) &
                         (df_o['contract']==row['contract'])].index[0]
        object_fullComment = df_o.iat[index, df_o.columns.get_loc('full_comment')]
        object_description = df_o.iat[index, df_o.columns.get_loc('description')]
        
        # Delete parameter's comment(s) if duplicate of parent object's (i.e., not parameter-specific)
        if (row['full_comment'] == object_fullComment) or ('@param' in object_fullComment):
            df_p.iat[i, df_p.columns.get_loc('full_comment')] = ''
        if row['description'] == object_description:
            df_p.iat[i, df_p.columns.get_loc('description')] = ''
        
    return df_p


def remove_license_comments(row):
    """Remove contract description if it's just about the software licensing"""
    
    description = row['description']
    if row['type'] == 'ContractDefinition' and any([(s in description) for s in ['License', 'Copyright']]):
        description = ''
    return description
    

# =============================================================================
# Basic coding based on keyword searching
# =============================================================================
CODING = {
    'proposal': {'keywords': ['Proposal', 'Propose'],
                 'topics': ['create', 'modify', 'execute', 'extend', 'cancel']}, 
    'membership': {'keywords': ['Member', 'Role'],
                   'topics': ['permission', 'responsibility', 'right', 'allow', 'require', 'forbid', 'authorize']},
    'voting': {'keywords': ['Vote', 'Voting', 'Ballot'],
              'topics': ['cast', 'delegate', 'change', 'tally', 'compute', 'referendum']} ,
    'dispute_resolution': {'keywords': ['Dispute', 'Adjudication', 'Arbitrator'],
                           'topics': ['juror', 'jury', 'evidence', 'ruling', 'appeal',
                                      'create', 'compute', 'execute', 'reward', 'penalty', 'sortition']},
    'reputation': {'keywords': ['Reputation'],
                   'topics': ['reward', 'penalty', 'penalize']},
    'election': {'keywords': ['Elect', 'Candidate'],
                 'topics': ['']}
}


def find_keywords_in_str(s, camelCase=False):
    """Return list of coding keys in string s
    
    Keywords are capitalized"""
    
    if s:
        if camelCase:
            kw = [c for c in CODING.keys() if any([(k in s) for k in CODING[c]['keywords']])]
            kw = kw + [c for c in CODING.keys() if any([(s.strip('_').lower().startswith(k.lower())) for k in CODING[c]['keywords']])]
        else:
            kw = [c for c in CODING.keys() if any([(k.lower() in s.lower()) for k in CODING[c]['keywords']])]
    else:
        kw = []

    return kw


def find_topics_in_str(s, kw, camelCase=False):
    """Return list of topics under the keyword 'kw' in string s
    
    Keywords are capitalized"""
    
    if s:
        if camelCase:
            topics = [t for t in CODING[kw]['topics'] if (t in s)]
            topics = topics + [t for t in CODING[kw]['topics'] if (s.strip('_').lower().startswith(t.lower()))]
        else:
            topics = [t for t in CODING[kw]['topics'] if (t.lower() in s.lower())]
    else:
        topics = []

    return topics


def find_keywords_in_obj(obj, df_params):
    """Return list of coding keys in an object's name or description"""
    
    kw_name = find_keywords_in_str(obj['object_name'], camelCase=True)
    kw_description = find_keywords_in_str(obj['description'])

    kw_params = []    
    try:
        params = df_params.loc[df_params['object_name'] == obj['object_name']]
        for i, param in params.iterrows():
            kw_params = kw_params + find_keywords_in_str(param['parameter_name'], camelCase=True)
            kw_params = kw_params + find_keywords_in_str(param['description'])
    except KeyError:
        pass
    
    return list(set(kw_name + kw_description + kw_params))


def find_topics_in_obj(obj, df_params):
    """Return list of topics in an object's name or description"""
    
    keywords = obj['coding_keyword_search']
    topics = []
    for kw in keywords:
        t_name = find_topics_in_str(obj['object_name'], kw=kw, camelCase=True)
        t_description = find_topics_in_str(obj['description'], kw=kw)

        t_params = []
        try:
            params = df_params.loc[df_params['object_name'] == obj['object_name']]
            for i, param in params.iterrows():
                t_params = t_params + find_topics_in_str(param['parameter_name'], kw=kw, camelCase=True)
                t_params = t_params + find_topics_in_str(param['description'], kw=kw)
        except KeyError:
            pass

        topics = topics + list(set(t_name + t_description + t_params))  
    
    return topics


# =============================================================================
# Main function
# =============================================================================
def parse_contract_file(uri, label=''):
    """Parse a Solidity contract file from a filepath or a URL
    
    If present, prepend 'label' to parsed AST filename for easier batch parsing
    
    returns df_objects, df_parameters"""
    
    assert (validators.url(uri) == True or os.path.isfile(uri)), 'supply a valid file path or URL'
    
    if validators.url(uri) == True:
        # Download content of file from URL 
        content = requests.get(uri).text
        fpath = 'tmp/solidity.txt'
        with open(fpath, 'w') as f:
            f.write(content)
        lines = content.split('\n')
        saveName = uri.split('/')[-1].split('.')[0]
    else:
        # Open existing file
        fpath = uri
        with open(fpath, 'r') as f:
            lines = f.readlines()
        saveName = os.path.splitext(os.path.split(uri)[-1])[0]

    # Get file structure as OrderedList and split into contracts
    sourceUnit = parser.parse_file(fpath, loc=True)
    
    # Save to file
    if label:
        saveName = label + '_' + saveName
    with open(f"tmp/parsed_{saveName}.txt", 'w') as f:
        pprint.pprint(sourceUnit, stream=f)    
    
    # Get object and parameter DataFrames (selecting from solidity_parser AST)
    df_objects, df_parameters = extract_objects_and_parameters(sourceUnit)
    
    # Add comments to the DataFrames
    df_objects, df_parameters = add_docstring_comments(lines, df_objects, df_parameters)
    df_parameters = add_inline_comments(lines, df_parameters)
    df_parameters = remove_duplicate_comments_in_parameters(df_objects, df_parameters)
    df_objects['description'] = df_objects.apply(remove_license_comments, axis=1)

    # Add coding keywords/topics to the DataFrames
    df_objects['coding_keyword_search'] = df_objects.apply(lambda row: find_keywords_in_obj(row, df_parameters), axis=1)
    df_objects['coding_topic_search'] = df_objects.apply(lambda row: find_topics_in_obj(row, df_parameters), axis=1)  
    
    return df_objects, df_parameters
