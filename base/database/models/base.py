
from typing import Dict
from .field import Field

from ...helper.decorator import cached
from ...helper.class_mixin import ReprMixin
from .statement import AND, Limit, OrderBy, SelectQuery


class ModelMeta(type):
    table_name: str
    __FIELDS__: Dict[str, Field]
    
    def __repr__(cls):
        return "<%s Model with %s Fields>" % (cls.__name__, len(cls.__FIELDS__))
    
    def __new__(cls, clsname, bases, attrs, **kw):
        new_attrs = {}
        fields = {}
        
        field_class = attrs.get('__FIELD_CLASS__') if attrs.get('__FIELD_CLASS__') is not None else Field
        if not issubclass(field_class, Field):
            raise RuntimeError('__FIELD_CLASS__ must be a subclass of Field.')
        
        if kw.get('inherit') is not None:
            kw.pop('inherit')
            [fields.update(_cls.__FIELDS__) for _cls in bases if isinstance(_cls, ModelMeta)]
        
        for name, value in attrs.items():
            if not isinstance(value, Field):
                new_attrs[name] = value
                continue
            fields[name] = field_class(value.type, value.name if value.name is not None else name, default=value.default, foreign_key=value.foreign_key, **value.opts)
        
        if attrs.get('__TABLE_NAME__') is not None:
            new_attrs['table_name'] = attrs.get('__TABLE_NAME__')
        else:
            new_attrs['table_name'] = clsname
        
        if attrs.get('__FIELDS__') is not None:
            fields = attrs.get('__FIELDS__')
            if isinstance(fields, list):
                fields = {field.name:field for field in fields}
        
        new_attrs.update({'__FIELDS__':fields, **fields})
        
        new_attrs['DB_MANAGER'] = attrs.get('DB_MANAGER')
        
        return super().__new__(cls, clsname, bases, new_attrs, **kw)
    
    def register_db_manager(cls, db_manager):
        "Registers a DB Manager for the corresponding model shorthands."
        cls.DB_MANAGER = db_manager


class Model(ReprMixin, metaclass=ModelMeta):
    _repr_format = "<%(classname)s Model instance with %(len(cls.__FIELDS__))s Fields>"
    
    def __getitem__(self, name):
        return self.__dict__.__getitem__(name)
    
    def __setattr__(self, name, value):
        if name in self.__class__.__FIELDS__:
            field = self.__class__.__FIELDS__.get(name)
            if field.is_valid(value):
                super().__setattr__(name, value)
    
    def __init__(self, _dict={}, *_, **kwargs):
        _dict.update(kwargs)
        for name, value in _dict.items():
            setattr(self, name, value)
    
    @property
    def valid(self):
        return all(map(lambda key:key in self.__dict__, self.__FIELDS__.values()))
    
    @classmethod
    @cached()
    def make_drop_query(cls):
        return """DROP TABLE IF EXISTS {table_name}""".format(table_name=cls.table_name)

    @classmethod
    @cached()
    def make_create_query(cls):
        _s = """CREATE TABLE IF NOT EXISTS "{table_name}"({queries})"""
        fields_queries = [field.generate_field_query() for field in cls.__FIELDS__.values()]
        field_queries = ", ".join([field_query[0] for field_query in fields_queries])
        modifier_queries = ", ".join([field_query[1] for field_query in fields_queries if len(field_query[1].strip())])
        queries = " ".join([field_queries, modifier_queries]).strip()
        return _s.format(table_name=cls.table_name, queries=queries)
    
    @classmethod
    @cached()
    def make_insert_query(cls, replace=False, ignore=False):
        command = "INSERT " +("INTO OR IGNORE" if ignore else "OR REPLACE INTO" if replace else "INTO")
        _s = "{command} {table_name} VALUES ({values_placeholder})".format(command=command, table_name=cls.table_name, 
                                                                            values_placeholder=','.join([':{}'.format(field.name) for field in cls.__FIELDS__.values()]))
        return _s
    
    def make_insert_values(self):
        entry_data = {}
        for name_in_obj, field in self.__FIELDS__.items():
            try:
                entry_data[field.name] = field.convert_value(self[name_in_obj])
            except KeyError:
                if not field.opts.get('NOT NULL', False):
                    entry_data[field.name] = None
                    continue
                if field.default is None and not field.opts.get('AUTO INCREMENT', False):
                    raise KeyError("'{}' is required but not found in data.".format(field.name))
                entry_data[field.name] = field.get_default_value()
        return entry_data
        
    def make_insert_args(self, replace=False, ignore=False):
        query = self.__class__.make_insert_query(replace=replace, ignore=ignore)
        values = self.make_insert_values()
        return (query, values)
    
    @classmethod
    def make_select_query(cls, comparator=None, orderby=None, limit=None):
        if isinstance(orderby, tuple):
            orderby = [orderby]
        if isinstance(limit, int):
            limit = [limit]
        return SelectQuery(table_name=cls.table_name, comparator=comparator, orderby=OrderBy(orderby), limit=Limit(*limit))
    
    @classmethod
    def make_delete_query(cls, comparator=None, delete_all=False):
        if comparator is None:
            if delete_all:
                return "DELETE FROM %s" % (cls.table_name)
            raise RuntimeError("make_delete_query is called with no comparator!") # protective measures
        return "DELETE FROM %s WHERE %s" % (cls.table_name, comparator.make_query())

    @classmethod
    def db_manager_registered(cls, raise_err=True):
        if cls.DB_MANAGER is None:
            if raise_err:
                raise RuntimeError("No DB Manager registered for model '{}'.".format(cls.__name__))
            return False
        return True
    
    @classmethod
    def create_table(cls):
        if cls.db_manager_registered():
            return cls.DB_MANAGER.create_table(cls)

    @classmethod
    def parse_from_db(cls, db_entry_data: dict):
        return cls({k: cls.__FIELDS__[k].invert_value_conversion(v) for k, v in db_entry_data.items()})

    @classmethod
    def get(cls, *comparators, **kwargs):
        if cls.db_manager_registered():
            comparators = AND(*comparators) if len(comparators) > 0 else None
            return cls.DB_MANAGER.get(cls, comparators, **kwargs)
    
    @classmethod
    def get_all(cls):
        if cls.db_manager_registered():
            return cls.DB_MANAGER.get_all(cls)

    @classmethod
    def delete(cls, *comparators):
        if cls.db_manager_registered():
            return cls.DB_MANAGER.delete(cls, AND(*comparators))

    def to_dict(self):
        return self.__dict__
