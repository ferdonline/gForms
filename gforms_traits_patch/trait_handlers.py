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
#  Author: David C. Morrill
#  Date:   06/21/2002
#
#  Refactored into a separate module: 07/04/2003
#
#  Patch of pull request #234
#
#------------------------------------------------------------------------------

"""
Defines the BaseTraitHandler class and a standard set of BaseTraitHandler
subclasses for use with the Traits package.

A trait handler mediates the assignment of values to object traits. It
verifies (via its validate() method) that a specified value is consistent
with the object trait, and generates a TraitError exception if it is not
consistent.
"""

from traits.trait_handlers import NoDefaultSpecified

#
#class TraitType ( BaseTraitHandler ):
#
def __init__ ( self, default_value = NoDefaultSpecified, **metadata ):
    """ This constructor method is the only method normally called
        directly by client code. It defines the trait. The
        default implementation accepts an optional, untype-checked default
        value, and caller-supplied trait metadata. Override this method
        whenever a different method signature or a type-checked
        default value is needed.
    """
    if default_value is not NoDefaultSpecified:
        self.default_value = default_value

    if len( metadata ) > 0:
        if len( self.metadata ) > 0:
            self._metadata = self.metadata.copy()
            self._metadata.update( metadata )
        else:
            self._metadata = metadata
        #defaults that private traits are not visible
        if self._metadata.get('private') and self._metadata.get('visible') is None:
            self._metadata['visible'] = False
        
    else:
        self._metadata = self.metadata.copy()
    
    self.init()

    
