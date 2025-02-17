from peewee import CharField, DateTimeField, TextField

from juniorguru.models.base import BaseModel


class PressRelease(BaseModel):
    id = CharField(primary_key=True)
    title = CharField()
    date = DateTimeField()
    lead = TextField(null=True)
    text = TextField()

    @classmethod
    def listing(cls):
        return cls.select().order_by(cls.date.desc())
