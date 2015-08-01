#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A GUI form generator for editing basic to complex data structures, with
type inference and validation.

The gForms utility may 'blindly' check the types and create fields accordingly,
or may be helped by the definition of a Model. For certain input types this is
necessary, as the value will not carry enough information about the type.

gForms accepts nested data structures definition, i.e., an entity may have
multiple other entities in its definition, and will create buttons linking to
the definition of these sub entities. Such nesting can be spceified by referring
to another Model Instance of by a dictionary object.

The type inspection mechanism can deal with mixed or imcomplete model definition,
i,e, A model definition will always be used if any of the entities (main/sub) have
a known (model) name, otherwise a model is created and instantiated dynamically.

Lists of same-type objects are fully supported, alowing *add, edit, remove* of
list elements, of the correct type. Lists of mixed types behave as objects -
its values are editable but without add or remove capabilities.

Models can be specified by extending the ClassModel class. Fields must be of either
-> base types: Int, Str, Complex, Float, Bool, Long, Unicode, Date, Time
-> Lists or Dictionaries: ListOfStr, SUBCLASS of ListClassModel
-> Other models: ModelInstance( other_model_class )

Models also accept data templates, which will render to a dropdown and live fill
all fields when a template is selected.

The edit() function is the main entry point for editing a data structure.

e.g.:
system = {
    'users': [ {'name':"F1", number:1}, {'name':"F2", number:2},  ],
    'location': 'Bytes Av, 16',
    'admin': {'name':"F1", number:1}
}
edit(system)

A more sophisticated version would be to define the model so that we can start
with an empty structure, and objects having "User" or "System" as class name will be recognized:

class User(ClassModel):
    name   = Str
    number = Int
    _templates={ 'user1': {'name':"F1", number:1},
                 'user2'  {'name':"F2", number:2} }
    
class UserList( ListClassModel ):
    _inner_type = User

class System(ClassModel):
    users    = UserList
    location = Str
    admin = ModelInstance( User )
mysystem = System() #Empty, but structure completely defined
mysystem = {        #Structure defined by individual fields, mixed objects and base values
    'users': ListClassModel(),
    'location': '',
    'admin': User()
}

For bug and other reports please contact fernando.pereira@cern.ch"

----------------------------------------------------------------------------
| Authors: F. Pereira, C. Theis
----------------------------------------------------------------------------  
"""
from __future__ import print_function

__author__ = "Fernando Pereira"
__email__ = "fernando.pereira@cern.ch"
__version__ = "0.2"
__status__ = "Development"   #"Prototype", "Development", or "Production".
__copyright__ = "Copyright (C) 2015 CERN"

from traits.trait_types import *
from traits.has_traits import HasTraits, HasPrivateTraits
from traits.trait_base import is_none
from traits.trait_errors import TraitError

from traitsui.editors import  *
from traitsui.view import View
from traitsui.item import Item

#Patch traits with a version GUI optimized, pull request #234
#--------------
from gforms_traits_patch import has_traits as has_traits_patch, trait_handlers as trait_handlers_patch
patched_has_traits = ['visible_traits','class_visible_traits', 'traits', 'trait_view', 'class_trait_view']
for patched_f in patched_has_traits: setattr( HasTraits, patched_f,  getattr(has_traits_patch, patched_f ) )
from traits import trait_handlers
trait_handlers.TraitType.__init__ = trait_handlers_patch.__init__
#--------------

#-------------------------------------------------------------------------------------------------
# gForms "public" API
#-------------------------------------------------------------------------------------------------
__all__ = [ 'Object', 'edit', 'get_or_create_editor_for_obj', 'register_api_type_handler',
            'ClassModel', 'ListClassModel', 
            'Str', 'Int', 'List', 'Dict', 'Bool', 'Enum', 'Password', 'ListOf', 'ListOfStr', 'ModelInstance','Instance','GenericTrait','Any'] #Exported Types

#-------------------------------------------------------------------------------------------------
# globals
#-------------------------------------------------------------------------------------------------
#Base container for data properties
class _O(object):pass
#Base flow Exception
class FormsException(Exception):pass

_logging = _O()
_logging.loglevel = 1 #logLevels not known yet
_logging.depth = 0
_logging.stream = sys.stdout

# ------- other existing globals, but initialized during program flow ------------
# _base_types_to_trait   #(dict) ->  base python types to trait types
# _registered_base_types #(list) ->  python types supported as base types
# _api_types_to_trait    #(dict) ->  API names to user-defined user model
# __dynamically_created_list_classes  #(dict) ->  ListClass names to ListClass subtypes
# --------------------------------------------------------------------------------

if _logging.loglevel >=4:
    from IPython.core.debugger import Tracer; debug_here = Tracer()


#==================================================================================================
#--------------------------------------------------------------------------------------------------
class Object(object):
    """A base object, initializable with a dictionary
    """
#--------------------------------------------------------------------------------------------------
    def __init__(self, init_dict = {}):
        self.__dict__.update( init_dict )
        
    def __new__(cls, obj = {} ):
        if type(obj) is dict:
            return super(Object, cls).__new__( cls, obj )
        
        if _is_list(obj):
            return obj
        else:
            #Try assigning directly
            return super(Object, cls).__new__( cls, vars(obj) )
    
    def __repr__(self):
        import pprint
        return "<%s%s>" % (self.__class__.__name__, pprint.pformat(self.__dict__) )



#-------------------------------------------------------------------------------------------------
#A new ListStr type, having the default editor set to ListStrEditor
#-------------------------------------------------------------------------------------------------
ListOfStr = List(str, editor=ListStrEditor( editable=True, auto_add=True ))


#==================================================================================================
# ClassModel base class. 
# It initializes a trait structure according to the object inner properties, converting if necessary
#==================================================================================================
class ClassModel(HasTraits): 
    """A new HastTraits class type which allows initialization with an object
    """
#--------------------------------------------------------------------------------------------------
    __orig_obj = Any(None, private=True)
    _templates = Dict( Str, Dict, private = True )
    Templates  = Any( private=True )

    #--------------------------------------------------------------------------------------------------
    def __init__(self, obj=None, **kw ):
        "ClassModel Constructor, accepting the initialization object (or dictionary)"
    #--------------------------------------------------------------------------------------------------
        HasTraits.__init__(self, **kw)

        if self._templates:
            self.add_trait( "Templates", Enum( "", self._templates.keys(), private=True, visible=True ) )

        if obj is not None:
            try:
                v = vars(obj)
            except TypeError:
                #Maybe its aready a dictionary -> not the most intended way
                self.set_init( obj ) #we leave this one to raise exception in case element cant be "iterized"
            else:
                self.set_init( v )
                self.__orig_obj = obj
    

    #--------------------------------------------------------------------------------------------------
    def _Templates_changed(self, old, new):
        """Handler for updating the properties when the template dropdown is changed"""
    #--------------------------------------------------------------------------------------------------
        try: self.set( **self._templates[new] )
        except KeyError:
            self.reset_traits()
    
    
    #Cant be done directly, since Arrays have to be converted to instances of ListClass Model
    #--------------------------------------------------------------------------------------------------
    def set_init(self, traits):
        """Initializes the trait structure, converting and assingning values"""
    #--------------------------------------------------------------------------------------------------
        invalid_keys = ["Templates"]
        mod_traits = {}

        for key,val in traits.iteritems():
            if key.startswith('_') or key in invalid_keys or val is None: continue   #Dont edit private fields
            
            if type(val) not in _registered_base_types and not _is_list(val):
                t = get_obj_t( _type_func(val) )
                if isinstance( t, List ): continue  # type and value dont match (this should be an exception, but in SUDS arrays are normal objects, expected to be replaced
                try:
                    iface, val = get_or_create_trait_for( val )
                    if self.__class_traits__[key].trait_type.__class__ == Generic:
                        log( LOG_LEVEL.DEBUG, "Changing trait type" )
                        del self.__class_traits__[key]
                        self.add_class_trait( key, iface )
                except Exception as e:
                    log( LOG_LEVEL.ERROR, "Could not create a trait from %s to assign to %s" %( str(val), key), "Error:", str(e) )
                    continue 
            
            #Check if value can be directly assigned
            try:
                x = self.validate_trait(key, val)
                mod_traits[key] = val
            except TraitError as e:
                #Trait exists, so its not generic. #Should be an object or a list of smtg
                if _is_list(val):
                    if len(val):
                        # Not generic incurs all elements being of same type
                        subt = _type_func(val[0]) 
                        tlistc = _getClassListOf(subt)
                        #Convert to the corresponding ClassList type
                        obj = tlistc(val)
                        mod_traits[key] = obj
                    else:
                        #Empty list -> no need for initializing
                        pass
                else:
                    # Looks like a base type it cant handle
                    log( LOG_LEVEL.ERROR, str(e) )
        
        return self.set(False, **mod_traits)
    
    
    #--------------------------------------------------------------------------------------------------
    def get_conv( self ):
        "Get the current object properties properly converted back"
    #--------------------------------------------------------------------------------------------------
        elems = self.get(private=is_none)
        _map_dic_values( lambda x: x.get_object() if isinstance(x, ClassModel) else x, elems) 
        return elems
    
    
    #--------------------------------------------------------------------------------------------------        
    def get_object( self, as_dict=False ):
        "Returns orig_object modified, or the fields as a dictionary"
    #--------------------------------------------------------------------------------------------------
        elems = self.get_conv()
        if as_dict:
            return elems 
        else:
            try:
                self.__orig_obj.__dict__.update(elems)  #--> need to convert back
                return self.__orig_obj
            except AttributeError:
                return self #Again should not happen. This means we're abusing the api and creating directly a ClassModel subclass. That's why __repr__ was implemented
    

    #--------------------------------------------------------------------------------------------------
    def __repr__(self):
        "The string representation of the object"
    #--------------------------------------------------------------------------------------------------
        import pprint
        return "<%s:%s>" % ( self.__class__.__name__, pprint.pformat(dict( (a,b) for a,b in self.__dict__.items() if a[0]!='_') ) )



#==================================================================================================
#--------------------------------------------------------------------------------------------------
class ListClassModel(ClassModel):
    """ A Trait class type for Lists of objects
        It directly supports adding and getting elements as if the object was the list itself
        Sets the default view to List view with the internal list objects, so that ojects can be added/deleted/edited.
    """
#--------------------------------------------------------------------------------------------------
    _inner_type = Any( None, private=True ) #base-type, or trait or Hastraits
    _orig_class = Any( None, private=True )
    
    #--------------------------------------------------------------------------------------------------
    def __init__(self, obj=None, trait_t=None, orig_class=None, **kw ):
        """ListClassModel contructor. 
           Accepts the list initialization and the inner type if it wasn't specified in the model"""
    #--------------------------------------------------------------------------------------------------
        if trait_t is not None:
            self._inner_type = trait_t
        trait_t = self._inner_type
        if trait_t is None:
            raise TraitError("Lists must have an inner type specified, in the least case 'Any'")
        
        if orig_class is not None:
            self._orig_class = orig_class
        orig_class = self._orig_class
        if orig_class is None:
            log( LOG_LEVEL.INFO, "List ", self.__class__.__name__, "does not have a original type to convert back")

        #Init on super class
        ClassModel.__init__(self, None, **kw)

        #Add the container object for the list, and specify the elements trait type
        t_edit = Any if trait_t == Any else Instance(trait_t, ())
        self.add_trait('_matrix', List(t_edit, editor=ListEditor() ) )
        
        if obj is not None and _is_list( obj ):
            #self._matrix = obj 
            for elem in obj:
                
                if trait_t == Any or isinstance(elem,trait_t):
                    self.append( elem )
                else:
                    #try:
                    self.append( trait_t( elem ) )
                    #except Exception as e:
                    #    log( LOG_LEVEL.WARN, "Element cant be converted to type", elem, trait_t.__class__, "Error:", str(e) )
        
    
    #--------------------------------------------------------------------------------------------------
    # Method implementing list container behavior
    #--------------------------------------------------------------------------------------------------
    def __iter__(self):
        return self._matrix.__iter__()
    
    def __getitem__(self, key):
        return self._matrix[key]
    
    def __add__(self, other):
        self._matrix += other
    
    def append( self, obj ):
        self._matrix.append( obj )
    
    def get_object( self, as_dict=False ):
        return [ GenericTrait.cast_back(elem, self._orig_class) for elem in self._matrix]
    #//eof----------------------------------------------------------------------------------------------

    #The gui editor will only display the list with the "custom" editor
    traits_view = View( Item("_matrix", style="custom", show_label=False), resizable=True, buttons=["OK", "Cancel"])




#==================================================================================================
#--------------------------------------------------------------------------------------------------
class GenericTrait( HasTraits ):
    """ Class creating a traits generic structure, dynamically initialiezed with data/types from obj.
        If the inner properties are other structures requests the creation of sub trait structure and properly links it.
        It keeps a reference to the original object and can return an updated version of it.
    """
#--------------------------------------------------------------------------------------------------
    __orig_obj = Any(None, private=True)
    __is_list = Bool(private=True)
    __is_dict = Bool(False, private=True)

    #--------------------------------------------------------------------------------------------------
    def __init__(self, obj, as_list=False ):
        """Contructor for a generic trait. Accepts an object, used for initialization.
        "as_list" flag shall be set to True in case the object is effectivelly a list but shall be
        rendered as an object, which is useful for mixed type lists"""
    #--------------------------------------------------------------------------------------------------
        HasTraits.__init__(self)
        self.__is_list = as_list
        
        #Get object properties or generate from list
        if as_list:
            obj_props = dict( ('pos'+str(i), value) for i, value in enumerate(obj) )
        else:
            try:
                obj_props = vars(obj)
                self.__orig_obj = obj
            except TypeError:
                #Maybe not the most intended way
                obj_props = obj
                self.__is_dict = True
        
        new_traits = self._create_get_traits( self.add_trait, obj_props )
        self.set( **new_traits )
    
    
    @staticmethod
    def _create_get_traits(add_trait_f, obj_props ):
        traits_ed = {}
        for key, value in obj_props.items():
            if key.startswith('_'): continue   #Dont edit private fields
            
            log( LOG_LEVEL.INFO, "Adding", key)
            t = _type_func( value )
            
            #We start by checking if the type is well known
            trait_t = get_obj_t( t )
            
            if trait_t is not None:
                t_inter, t_obj = get_or_create_trait_for( value )
                add_trait_f( key, t_inter )
                traits_ed[key] = t_obj
            elif t in _registered_base_types:
                trait_t = _registered_base_types[type(value)]
                add_trait_f( key, trait_t )
                traits_ed[key] = value if value is not None else trait_t.default_value
            else:
                t_inter, t_obj = get_or_create_trait_for( value )
                add_trait_f( key, t_inter )
                traits_ed[key] = t_obj
            
        return traits_ed
    
    
    #--------------------------------------------------------------------------------------------------
    def __getitem__( self, key ):
        """Gets a item in position key in case the object is a list. Otherwise raises TypeError"""
    #--------------------------------------------------------------------------------------------------
        if not self.__is_list:
            raise TypeError("The current object doesnt represent a list")
        
        return getattr( self, 'pos' + str(key) )

    #--------------------------------------------------------------------------------------------------
    def __setitem__( self, key, value ):
        """Sets the value in position key in case the object is a list. Otherwise raises TypeError"""
    #--------------------------------------------------------------------------------------------------
        if not self.__is_list:
            raise TypeError("The current object doesnt represent a list")
        
        return setattr( self, 'pos' + str(key), value )

    
    #--------------------------------------------------------------------------------------------------
    def get_object( self, as_dict=False ):
        """Returns the object, either its data in dict form (as_dict=True)
        or the updated original object (default)"""
    #--------------------------------------------------------------------------------------------------
        elems=self.get( private=is_none )
        elems=dict( (key, self.cast_back(value) ) for key,value in elems.iteritems() )

        if not self.__is_list:
            if as_dict or self.__is_dict:
                return elems 
            self.__orig_obj.__dict__.update( elems )
            return self.__orig_obj
        else:
            #For lists cant return dict representation
            keys = sorted( elems.keys() ) #Important to keep order
            return [ elems[key] for key in keys ]


    
    @staticmethod
    #--------------------------------------------------------------------------------------------------
    def cast_back( obj, cast_to=None ):
        """Class function which returns the correct representation of a value, even if it has to
        recursivelly convert it by calling the obj get_object() method"""
    #--------------------------------------------------------------------------------------------------
        t = _type_func(obj)
        if t in _registered_base_types:
            return obj
        else:
            #Pure lists are not returned pure! Grrrr
            if t == TraitListObject:
                return list(obj)
            
            #else (returns)
            if cast_to is None:
                return obj.get_object()
            
            #If needs cast_to (mostly for newly created list items)
            try:
                new_obj = cast_to() #Create instance, please accept empty args!
            except:
                log( LOG_LEVEL.ERROR, "Class", cast_to, "should implement contructor without arguments. Unexpected behavior might arise" )
                return obj
            else:
                new_obj.__dict__.update( obj.get_object(as_dict=True)  )
                return new_obj
            


#==================================================================================================
class ModelInstance( Instance ):
    """Helper class for the model, defining a link to an instance of an object"""
#--------------------------------------------------------------------------------------------------
    def __init__(self, klass = None, **metadata):
      return super(ModelInstance, self).__init__(klass, (), **metadata)


  
 
################################################################################################
##  TYPE HANDLING - Definition of base types, Model types, and dynamic creation of list types
################################################################################################ 

#==================================================================================================
# Base type definitions
#==================================================================================================
_base_types_to_trait = {
    bool       : Bool,
    int        : Int,
    str        : CStr,
    long       : Long,
    float      : Float,
    complex    : Complex,
    unicode    : CStr,
    type(None) : Generic,
    datetime.datetime : Any,
    datetime.date     : Date,
    datetime.time     : Time
}
#==================================================================================================
class BaseTypes(object):
    """List extension to allow verification by subclass"""
#--------------------------------------------------------------------------------------------------
    def __init__(self, dic):
        self.dic = dict(dic)

    def __contains__(self, val):
        return any( [ issubclass(val, t) for t in self.dic.iterkeys() ] )
    
    def __getitem__(self, key):
        for k,v in self.dic.iteritems():
            if issubclass( key, k ):
                return v
        return None

# The BaseTypes container singleton
_registered_base_types = BaseTypes(_base_types_to_trait)
#//--------------------------------------------------------------------------------------------------


# ==================================================================================================
# Data structure and accessor methods for holding dynamically created list class types
#--------------------------------------------------------------------------------------------------
__dynamically_created_classes = {}

def _getClassListOf( innerClass ):
    name = "ListOf" + getattr(innerClass, '__name__')
    return __dynamically_created_classes.get( name )

def _setClassListOf( innerClass, new_class ):
    name = "ListOf" + getattr(innerClass, '__name__')
    __dynamically_created_classes[name] = new_class

def _get_or_create_ClassListOf( innerClass, orig_class=None ):
    name = "ListOf" + getattr(innerClass, '__name__')
    return __dynamically_created_classes.get( name ) \
           or _create_ListClass( name, innerClass, orig_class=orig_class )

def _create_ListClass( name, innerClass, orig_class=None ):
    log( LOG_LEVEL.DEBUG, "   > Creating dynamic ListClass", name )
    def init(m_self, obj=None, **kw):
        ListClassModel.__init__(m_self, obj, innerClass, **kw)
    listClass = type(name, (ListClassModel,), dict( __init__ = init, _orig_class=orig_class ) )
    __dynamically_created_classes[name] = listClass
    return listClass

def _create_ModelClass( name, obj ):
    log( LOG_LEVEL.DEBUG, "   > Creating dynamic model", name )
    obj_props = vars(obj) #Objects only in here. Dicts must turn into GenericTrait
    def init(m_self, m_obj=None, **kw):
        ClassModel.__init__(m_self, m_obj, **kw )
    newClassModel = type(name, (ClassModel,), dict( __init__ = init, ) )
    GenericTrait._create_get_traits( newClassModel.add_class_trait, obj_props )
    __dynamically_created_classes[name] = newClassModel
    return newClassModel

def get_or_create_ModelClass_for_obj( obj ):
    t_name = _type_func( obj ).__name__
    return __dynamically_created_classes.get( t_name ) \
           or _create_ModelClass( t_name, obj )
    

#==================================================================================================
def ListOf( Klass, **metadata):
    """Returns a List trait, whose elements shall be of type Klass.
      It properly gets/sets a new List type, according to type, so that lists hold a type info and
      can be converted back to their List model object"""
#--------------------------------------------------------------------------------------------------
    if Klass in _registered_base_types:
        return List( Klass, editor = ListStrEditor( editable=True, auto_add=True ), **metadata )
    else:
        return ModelInstance( _get_or_create_ClassListOf( Klass ) )

#//eof---------------------------------------------------------------------------------------------



#==================================================================================================
# Model type definitions
#--------------------------------------------------------------------------------------------------
_api_types_to_trait = {}

#==================================================================================================
def get_obj_t( obj_t ):
    """ Returns the Trait class from the object, if defined. Otherwise return None
    """
#--------------------------------------------------------------------------------------------------
    cls_name = obj_t.__name__
    return _api_types_to_trait.get( cls_name ) or \
            __dynamically_created_classes.get( cls_name )
    



################################################################################################
##  FUNCTIONS FOR LOOKUP AND DYNAMIC OBJECTS CREATION - Core generic trait logic 
################################################################################################ 

#==================================================================================================
def create_list_trait( obj ):
    """ Creates a Trait for a list-type object.
        In case the list has objects all of the same class type, a ListClassModel Instance interface is presented to the user.
        If all the objects are python primary types, a Inline editor is presented
        Otherwise (mixed) it is transformed into an object editor, disallowing deletion and addition of new objects.
    """
#--------------------------------------------------------------------------------------------------
    #Object is iterable, so we can create a list editing obj
    types = tuple(set( map(_type_func, iter(obj) ) ))
    
    t_count = len(types)
    
    if t_count == 1:
        t = types[0]
        if t in _registered_base_types:
            log( LOG_LEVEL.DEBUG, " ... of known base type:", t.__name__ )
            if t == str:
                t_inter = ListOfStr
                return t_inter, obj
            
            t_obj = obj
            t_inter = List( t, editor = ListStrEditor( editable=True, auto_add=True ) )
        
        else:
            model = get_obj_t(t)
            
            if model is None:
                if hasattr( obj[0], "__dict__" ):
                    log( LOG_LEVEL.DEBUG, " ... of unknown type", t.__name__ )
                    model = get_or_create_ModelClass_for_obj( obj[0] )
                else:
                    #We are facing a type without __dict__, -> no way to recreate objects
                    log( LOG_LEVEL.DEBUG, " Converting list to Generic due to inner type:", t.__name__ )
                    t_obj = GenericTrait(obj, as_list = True)
                    t_inter = Instance(GenericTrait)
                    return t_inter, t_obj
            else:
                log( LOG_LEVEL.DEBUG, " ... of existing Model", model.__name__ )
            
            #ListClasses now need an orig_class, so that new objects can be transformed into original objects
            listClass = _get_or_create_ClassListOf( model, _type_func(obj[0]) )
            
            log( LOG_LEVEL.MORE_INFO, " Initializing instance of %s with %d elements" % (listClass.__name__,len(obj),))
            t_obj = listClass( obj )
            t_inter = Instance(ListClassModel)
    else:
         #Oh my... mixed array
         # -> create an object with the mixes? names?
         t_obj = GenericTrait(obj, as_list = True)
         t_inter = Instance(GenericTrait)

    return t_inter, t_obj



#==================================================================================================
def create_generic_trait( obj ):
    """ Creates a generic Trait object given any object.
    Default is to create a GenericTrait trait initted to object.
    If object is an iterable will return a ListClassModel trait, initialized with the elements type
    if is is consistent. Otherwise the type is GenericTrait
    """
#--------------------------------------------------------------------------------------------------
    if _is_list( obj ):
        log( LOG_LEVEL.INFO, "Type", _type_func(obj), "-> Creating list trait" )
        t_inter, trait_obj = create_list_trait( obj )
    else:
        log( LOG_LEVEL.INFO, "Type", _type_func(obj), "-> Creating Generic trait" )
        
        #Try create a new Model dynamically - not available for dicts
        try:
            obj_props = vars(obj)
        except TypeError:
            #The most generic way
            trait_obj = GenericTrait(obj)
            t_inter = Instance(GenericTrait, ())
        else:
            newModel = get_or_create_ModelClass_for_obj( obj )
            t_inter = Instance(newModel, ())
            trait_obj = newModel( obj )
    return t_inter, trait_obj



#==================================================================================================
def get_or_create_trait_for( obj ):
    """ Gets the corresponding trait class, or uses the generic one, and instantiates with the current object.
    This allows any object to be validated and rendered despite the model completeness. When the model is available
    all the fields are processed accordingly.
    """
#--------------------------------------------------------------------------------------------------
    # If we were already given a model object, return it
    if isinstance(obj, HasTraits):
        return Instance(obj, ()), obj
    
    _logging.depth +=1

    #Lookup handling class
    trait_t = get_obj_t( _type_func(obj) )
    log( LOG_LEVEL.MORE_INFO, "Found trait_t", trait_t )
    
    if trait_t is not None:
        log( LOG_LEVEL.INFO, "Type", _type_func(obj), "Converted to", trait_t )
        trait_obj = trait_t( obj )
        t_inter = Instance(trait_t, ())
    else:
        t_inter, trait_obj = create_generic_trait( obj )

    _logging.depth -=1
    return t_inter, trait_obj



#==================================================================================================
def get_or_create_editor_for_obj( obj ):
    """Function retrieving or creating a corresponding HasTraits class to the object.
    The result can be used as well as part of other HasTraits, cast'ed to Instance trait."""
#--------------------------------------------------------------------------------------------------   
    # If we were already given a model object, return it
    if isinstance(obj, HasTraits):
        return obj
    
    t_inter, t_obj = get_or_create_trait_for( obj )
    return t_obj



#==================================================================================================
def edit( obj, replace=True ):
    """Magic function allowing editing of any object.
    It turns the object into a complex trait object, by introspection, and displays a Gui for editting.
    """
#--------------------------------------------------------------------------------------------------
    trait_ed = get_or_create_editor_for_obj( obj )
    trait_ed.configure_traits()
    
    #Apply result
    if replace:
        try:
            obj.__dict__.update( trait_ed.get_object(True) )
        except AttributeError:
            obj.update( trait_ed.get_object(True) )
        return obj

    return trait_ed.get_object()
    


#==================================================================================================
# Auxiliary public API
#==================================================================================================
def register_api_type_handler( **types ):
    "Handles the api types specified as argument names with the argument value Handler"
#--------------------------------------------------------------------------------------------------
    _api_types_to_trait.update(types)




################################################################################################
# AUXILIARY functions, but might be publicly used
################################################################################################

#==================================================================================================
def _type_func( obj ):
    """Using __class__ covers SUDS cases, but literals might need type"""
#--------------------------------------------------------------------------------------------------
    try:
        return obj.__class__
    except:
        return type(obj)


#==================================================================================================
def _is_list( obj ):
    """Defines whether an object shall be considered a list for trait purposes."""
#--------------------------------------------------------------------------------------------------
    return hasattr(obj, "__add__") and hasattr(obj, "__len__")


#==================================================================================================
def _map_dic_values( f, d ):
    """A version of the map() function operating over the values of a dictionary"""
#--------------------------------------------------------------------------------------------------
    for k, v in d.iteritems():
        d[k] = f(v)



################################################################################################
# AUXILIARY functions, private
################################################################################################

class LOG_LEVEL:
    DEBUG     = 4
    MORE_INFO = 3
    INFO      = 2
    WARN      = 1
    ERROR     = 0
    
    _description = dict( (v,k) for k,v in vars().iteritems() if type(v) is int )
    
    @classmethod
    def get_description( cls, LogLevel ):
        return cls._description[ LogLevel ]


def log( level, *message ):
    if _logging.loglevel >= level:
        print( "[%10s]"%(LOG_LEVEL.get_description(level),), "  " * _logging.depth, ">", *message, file=_logging.stream)
    
