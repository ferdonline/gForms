# gForms
### A GUI form generator for editing basic to complex data structures, with type inference and validation.

## Fields
The gForms utility may 'blindly' check the types and create fields accordingly, or may be helped by the definition of a Model. For certain input types this is necessary, as the value will not carry enough information about the type.

### Nested structures
gForms accepts nested data structures definition, i.e., an entity may have multiple other entities in its definition, and will create buttons linking to the definition of these sub entities. Such nesting can be spceified by referring to another Model Instance of by a dictionary object.

The type inspection mechanism can deal with mixed or imcomplete model definition, i,e, A model definition will always be used if any of the entities (main/sub) have a known (model) name, otherwise a model is created and instantiated dynamically.

### Lists
Lists of same-type objects are fully supported, alowing *add, edit, remove* of list elements, of the correct type. Lists of mixed types behave as objects - its values are editable but without add or remove capabilities.

## Advanced - Model specification
Models can be specified by extending the ClassModel class. Fields must be of either 
  - base types: Int, Str, Complex, Float, Bool, Long, Unicode, Date, Time 
  - Lists or Dictionaries: ListOfStr, SUBCLASS of ListClassModel -> Other models: ModelInstance( other_model_class )

## Templates
Models also accept data templates, which will render to a dropdown and live fill all fields when a template is selected.

The edit() function is the main entry point for editing a data structure.

# Examples
## 1 Simple, with nested data
```python
system = {
    'users': [ {'name':"F1", number:1}, {'name':"F2", number:2},  ],
    'location': 'Bytes Av, 16',
    'admin': {'name':"F1", number:1}
}
edit(system)
```

## 2 Defining a model
A more sophisticated version would be to define the model so that we can start with an empty structure, and objects having "User" or "System" as class name will be recognized:

```python
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
```
For bug and other reports please contact
