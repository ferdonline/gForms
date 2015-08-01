#------------------------------------------------------------------------------
#
#  Copyright (c) 2005, Enthought, Inc.
#  All rights reserved.
#
#  This software is provided without warranty under the terms of the BSD
#  license included in enthought/LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#
#  Thanks for using Enthought open source!
#
#  Author:        David C. Morrill
#  Original Date: 06/21/2002
#
#  Rewritten as a C-based type extension: 06/21/2004
#
#  Patch of pull request #234
#
#------------------------------------------------------------------------------

# Necessary entities from mainstream class
from traits.has_traits import not_event, not_false, FunctionType

#
#class TraitType ( BaseTraitHandler ):
#
def trait_view ( self, name = None, view_element = None ):
    """ Gets or sets a ViewElement associated with an object's class.
    """
    return self.__class__._trait_view( name, view_element,
                        self.default_traits_view, self.trait_view_elements,
                        self.visible_traits, self )

def class_trait_view ( cls, name = None, view_element = None ):
    return cls._trait_view( name, view_element,
              cls.class_default_traits_view, cls.class_trait_view_elements,
              cls.class_visible_traits, None )

class_trait_view = classmethod( class_trait_view )
    

def visible_traits ( self ):
    """Returns an alphabetically sorted list of the names of non-event
    trait attributes associated with the current object, that should be GUI visible
    """
    return self.trait_names( type = not_event, editable = not_false, visible = not_false )

def class_visible_traits ( cls ):
    """Returns an alphabetically sorted list of the names of non-event
    trait attributes associated with the current class.
    """
    return cls.class_trait_names( type = not_event, editable = not_false, visible = not_false )

class_visible_traits = classmethod( class_visible_traits )


def traits ( self, **metadata ):
    """Returns a dictionary containing the definitions of all of the trait
    attributes of this object that match the set of *metadata* criteria.

    """
    traits = self.__base_traits__.copy()
    #Update with instance defined traits
    for name, trt in self._instance_traits().iteritems():
        if name[-6:] != "_items":
            traits[name] = trt


    for name in self.__dict__.keys():
        if name not in traits:
            trait = self.trait( name )
            if trait is not None:
                traits[ name ] = trait

    if len( metadata ) == 0:
        return traits

    for meta_name, meta_eval in metadata.items():
        if type( meta_eval ) is not FunctionType:
            metadata[ meta_name ] = _SimpleTest( meta_eval )

    result = {}
    for name, trait in traits.items():
        for meta_name, meta_eval in metadata.items():
            if not meta_eval( getattr( trait, meta_name ) ):
                break
        else:
            result[ name ] = trait

    return result

    