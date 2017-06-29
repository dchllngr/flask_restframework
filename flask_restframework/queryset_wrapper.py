#coding: utf8
from mongoengine.base.document import BaseDocument
from mongoengine.queryset.queryset import QuerySet
from pymongo.cursor import Cursor


class InstanceWrapper(object):

    def __init__(self, item):
        self.item = item

    def get_id(self):
        """
        Возвращает id записи
        """
        raise NotImplementedError

    def get_field(self, key):
        """
        Возвращает значение поля key для обернутой записи
        """
        raise NotImplementedError

    def update(self, validated_data):
        raise NotImplementedError

    def to_dict(self):
        """
        Should return dict representation of instance
        """
        raise NotImplementedError


class MongoInstanceWrapper(InstanceWrapper):

    def to_dict(self):
        return self.item.to_mongo()

    def get_id(self):
        return self.item.id

    def update(self, validated_data):
        for key, value in validated_data.items():
            setattr(self.item, key, value)

        self.item.save()


    def get_field(self, key):
        out = self.item

        for part in key.split("__"):
            try:
                out = getattr(out, part)
            except:
                return None

        if isinstance(out, (BaseDocument, dict)):
            return MongoInstanceWrapper(out)
        elif isinstance(out, list):
            r = []
            for item in out:
                if isinstance(item, (BaseDocument, dict)):
                    r.append(MongoInstanceWrapper(item))
                else:
                    r.append(item)

            return r

        return out


class CursorInstanceWrapper(InstanceWrapper):

    def to_dict(self):
        return dict(self.item)

    def get_id(self):
        return self.item["_id"]

    def get_field(self, key):
        if key == "id":
            key = "_id"
        out = self.item.get(key)
        if isinstance(out, dict):
            return CursorInstanceWrapper(out)
        if isinstance(out, list):
            r = []

            for item in out:
                if isinstance(item, dict):
                    r.append(CursorInstanceWrapper(item))
                else:
                    r.append(item)

            return r

        return out

class QuerysetWrapper(object):

    def __init__(self, data, wrapperType):
        self.wrapperType = wrapperType
        self.data = data

    @classmethod
    def from_queryset(cls, qs):
        if isinstance(qs, QuerySet):
            return MongoDbQuerySet(qs, MongoInstanceWrapper)
        elif isinstance(qs, Cursor):
            return CursorQuerySet(qs, CursorInstanceWrapper)
        elif callable(qs):
            return cls.from_queryset(qs())
        elif isinstance(qs, QuerysetWrapper):
            return qs

        raise TypeError("Unknown type {}".format(type(qs)))

    def get(self, id):
        #type: (Any)->InstanceWrapper
        """Should return one instance by it id"""

        raise NotImplementedError

    def get_data(self):
        #type: ()->List[InstanceWrapper]
        """
        Returns iterable of InstanceWrapper
        """

        for item in self.data:
            yield self.wrapperType(item)

    @classmethod
    def from_instance(cls, value):
        return DummyQuerySet(value)

    def count(self):
        """
        Should return total count of items in QuerySet
        """
        raise NotImplementedError

    def slice(self, frm, to):
        """
        Should slice queryset
        """
        raise NotImplementedError

    def filter_by(self, **filters):
        """
        Should filter queryset by filters (Django style filtering)
        Returns new queryset
        """
        raise NotImplementedError


class DummyQuerySet(QuerysetWrapper):

    def __init__(self, item):
        self.data = [item]

    def get_data(self):
        return self.data

class MongoDbQuerySet(QuerysetWrapper):

    def filter_by(self, **filters):
        return MongoDbQuerySet(self.data.filter(**filters), self.wrapperType)

    def slice(self, frm, to):
        return MongoDbQuerySet(self.data[frm:to], self.wrapperType)

    def get(self, id):
        return self.wrapperType(self.data.get(id=id))

    def count(self):
        return self.data.count()

class CursorQuerySet(QuerysetWrapper):

    def __init__(self, *a, **k):
        super(CursorQuerySet, self).__init__(*a, **k)
        self.data = list(self.data)

    def count(self):
        return len(self.data)

    def filter_by(self, id=None):
        return CursorQuerySet(filter(
            lambda item: item["_id"]==id,
            self.data
        ), wrapperType=self.wrapperType)

    def slice(self, frm, to):
        return self.data[frm: to]

