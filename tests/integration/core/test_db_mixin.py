import datetime
import json
from io import StringIO

import pytest
from django.contrib.postgres.fields import ArrayField
from django.db import models

from aap_eda.core.models import Project, base


def test_oid_field_int():
    assert base.OIDField == models.IntegerField


def test_copyfy_class():
    assert str(base.Copyfy(None)) == base.DEFAULT_NULL
    assert str(base.Copyfy("eek")) == "eek"
    assert str(base.Copyfy(1)) == "1"


def test_copyfydict():
    d = {"star": "trek", "quatloos": 200}
    assert str(base.CopyfyDict(d)) == json.dumps(d)
    assert str(base.CopyfyDict({})) == "{}"
    assert str(base.CopyfyDict(None)) == base.DEFAULT_NULL


def test_copyfylisttuple():
    assert str(base.CopyfyListTuple(list("asdf"))) == "{a,s,d,f}"
    assert str(base.CopyfyListTuple([])) == "{}"
    assert str(base.CopyfyListTuple(None)) == base.DEFAULT_NULL
    assert str(base.CopyfyListTuple([[1,2],[3,4]])) == "{{1,2},{3,4}}"


def test_adapt_copy_types():
    vals = [
        1,
        "eek",
        None,
        {"feels": "meh"},
        datetime.datetime.now(tz=datetime.timezone.utc),
        [1,2,3,4],
    ]
    mvals = base.adapt_copy_types(vals)
    assert type(mvals) == list
    assert len(mvals) == len(vals)
    assert type(mvals[0]) == int
    assert type(mvals[1]) == str
    assert type(mvals[2]) == base.Copyfy
    assert str(mvals[2]) == base.DEFAULT_NULL
    assert type(mvals[3]) == base.CopyfyDict
    assert type(mvals[4]) == datetime.datetime
    assert type(mvals[5]) == base.CopyfyListTuple

    mvals = base.adapt_copy_types(tuple(vals))
    assert type(mvals) == tuple


def test_copyfy_values(db):
    vals = [
        1,
        "eek",
        None,
        {"feels": "meh"},
        datetime.datetime.now(tz=datetime.timezone.utc),
        [1,2,3,4],
    ]
    mvals = base.copyfy_values(vals)
    assert isinstance(mvals, str)
    assert base.DEFAULT_SEP in mvals
    mvals_list = mvals.split(base.DEFAULT_SEP)
    assert len(mvals_list) == len(vals)
    assert mvals_list[0] == str(vals[0])
    assert mvals_list[1] == str(vals[1])
    assert mvals_list[2] == base.DEFAULT_NULL
    assert mvals_list[3] == json.dumps(vals[3])
    assert mvals_list[4] == str(vals[4])
    assert mvals_list[5] == str(base.CopyfyListTuple(vals[5]))


@pytest.mark.django_db
def test_copy_to_table():
    from django.db import connection as db

    with db.cursor() as cur:
        cur.execute(
            """
create table eek (
    id serial primary key,
    label text not null,
    data jsonb,
    lista int[],
    created_ts timestamptz
)
;
            """
        )

    class Eek(models.Model):
        class Meta:
            app_label = "core"
            db_table = "eek"
        label = models.TextField(null=False)
        data = models.JSONField()
        lista = ArrayField(models.IntegerField())
        created_ts = models.DateTimeField()

    try:
        cols = ["label", "data", "lista", "created_ts"]
        vals = [
            [
                "label-1",
                {"type": "rulebook", "data": {"ruleset": "ruleset-1"}},
                None,
                datetime.datetime.now(tz=datetime.timezone.utc),
            ],
            [
                "label-2",
                None,
                [1,2,3,4],
                datetime.datetime.now(tz=datetime.timezone.utc),
            ],
        ]

        copy_file = StringIO()
        for val in vals:
            print(base.copyfy_values(val), file=copy_file)  # noqa:T201
        copy_file.seek(0)

        rc = base.copy_to_table(
            db,
            "eek",
            cols,
            copy_file,
        )
        assert rc

        res = list(Eek.objects.values_list())
        assert len(res) == 2
        for i, rec in enumerate(res):
            val = vals[i]
            for j in range(len(rec)):
                if j == 0:
                    assert isinstance(rec[j], int)
                else:
                    assert val[j - 1] == rec[j]

    finally:
        with db.cursor() as cur:
            cur.execute(
                """
drop table eek;
                """
            )


@pytest.mark.django_db
def test_copy_to_table_with_sep():
    from django.db import connection as db

    with db.cursor() as cur:
        cur.execute(
            """
create table eek (
    id serial primary key,
    label text not null,
    data jsonb,
    lista int[],
    created_ts timestamptz
)
;
            """
        )

    class Eek(models.Model):
        class Meta:
            db_table = "eek"
        label = models.TextField(null=False)
        data = models.JSONField()
        lista = ArrayField(models.IntegerField)
        created_ts = models.DateTimeField()

    try:
        cols = ["label", "data", "lista", "created_ts"]
        vals = [
            [
                "label-1",
                {"type": "rulebook", "data": {"ruleset": "ruleset-1"}},
                None,
                datetime.datetime.now(tz=datetime.timezone.utc),
            ],
            [
                "label-2",
                None,
                [1,2,3,4],
                datetime.datetime.now(tz=datetime.timezone.utc),
            ],
        ]

        copy_file = StringIO()
        for val in vals:
            print(base.copyfy_values(val, sep="|"), file=copy_file)  # noqa:T201
        copy_file.seek(0)

        rc = base.copy_to_table(
            db,
            "eek",
            cols,
            copy_file,
            sep="|"
        )
        assert rc

        res = list(Eek.objects.values_list())
        assert len(res) == 2
        for i, rec in enumerate(res):
            val = vals[i]
            for j in range(len(rec)):
                if j == 0:
                    assert isinstance(rec[j], int)
                else:
                    assert val[j - 1] == rec[j]

    finally:
        with db.cursor() as cur:
            cur.execute(
                """
drop table eek;
                """
            )


def test_copyfy_model():
    now = (datetime.datetime.now(tz=datetime.timezone.utc),)
    kwargs = {
        "name": "proj-1",
        "description": "test project",
        "created_at": now,
        "modified_at": now,
    }
    p = Project(**kwargs)
    p_mog = p.copyfy()
    p_mog_values = p_mog.split(base.DEFAULT_SEP)
    assert len(p_mog_values) == len(p._meta.concrete_fields)


def test_copyfy_model_with_sep():
    now = (datetime.datetime.now(tz=datetime.timezone.utc),)
    kwargs = {
        "name": "proj-1",
        "description": "test project",
        "created_at": now,
        "modified_at": now,
    }
    p = Project(**kwargs)
    p_mog = p.copyfy(sep="|")
    p_mog_values = p_mog.split("|")
    assert len(p_mog_values) == len(p._meta.concrete_fields)


def test_copyfy_model_with_fields():
    now = (datetime.datetime.now(tz=datetime.timezone.utc),)
    kwargs = {
        "name": "proj-1",
        "description": "test project",
        "created_at": now,
        "modified_at": now,
    }
    p = Project(**kwargs)
    mog_fields = ["name", "description"]
    p_mog = p.copyfy(fields=mog_fields)
    p_mog_values = p_mog.split(base.DEFAULT_SEP)
    assert len(p_mog_values) == len(mog_fields)
    assert str(now) not in p_mog
