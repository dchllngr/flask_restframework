from mongoengine.base.document import BaseDocument
from mongoengine.queryset.queryset import QuerySet
from pymongo.cursor import Cursor


class InstanceWrapper(object):

    def __init__(self, item):
        self.item = item

    def get_field(self, key):
        """
        Возвращает значение поля key для обернутой записи
        """
        raise NotImplementedError


class MongoInstanceWrapper(InstanceWrapper):

    def get_field(self, key):
        out = None

        for part in key.split("__"):
            try:
                out = getattr(self.item, part)
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


class DummyQuerySet(QuerysetWrapper):

    def __init__(self, item):
        self.data = [item]

    def get_data(self):
        return self.data

class MongoDbQuerySet(QuerysetWrapper):

    def slice(self, frm, to):
        return MongoDbQuerySet(self.data[frm:to], self.wrapperType)

    def get(self, id):
        pass

    def count(self):
        return self.data.count()

class CursorQuerySet(QuerysetWrapper):
    pass

