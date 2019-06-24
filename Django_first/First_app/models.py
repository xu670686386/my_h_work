#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.db import models
from django.db import connection, transaction
from datetime import datetime


# Create your models here.


def list_to_str(ls):
    if ls is None or len(ls) == 0:
        return "()"
    else:
        return "({})".format(",".join([str(i) for i in ls]))


class Tags(models.Model):
    code = models.CharField(
        max_length=64, null=True, default=None, unique=True)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=256, null=True)
    father = models.ForeignKey(
        'self', null=True, blank=True, verbose_name='上级标签')

    # @classmethod
    # def tags_trees(cls, father_id):
    #     rs = cls.objects.all()

    @classmethod
    def children_tags_one(cls, father_id):
        rs = cls.objects.filter(father__id=father_id)
        results = []
        for r in rs:
            t = dict(id=r.id, name=r.name)
            if r.father is not None:
                t['father_id'] = r.father.id
            results.append(t)
        return results

    @classmethod
    def all_tags(cls):
        t_names = []
        with connection.cursor() as cursor:
            cursor.execute("select id, name, father_id from vtags_tags order by id;")
            # 去掉已经存在的ID
            r = cursor.fetchone()
            while r is not None:
                t_names.append(r[1])
                r = cursor.fetchone()
        return t_names


class VideoFragments(models.Model):
    STATUS_EDIT = 0
    STATUS_READY = 1
    STATUS_CUTTING = 2
    STATUS_CUT = 3
    STATUS_TRANSLATE = 4
    STATUS_SUCCESS = 1000
    STATUS_FAILURE = 1001
    # 0编辑中；1完成；2切分片段中；3:切片完成；4:转码中；1000完成；1001异常完成
    STATUS = {
        0: '编辑中',
        1: '准备切片中',
        2: '切分片段中',
        3: '切片完成',
        4: '转码中',
        1000: '转码完成',
        1001: '异常完成'
    }
    origin_asset_id = models.IntegerField(
        null=False, default=0, db_index=True)  # 没有外键是想减少关联性；
    origin_asset_key = models.CharField(
        max_length=64, null=True, default=None)  # 原始素材的key
    tags = models.ManyToManyField(Tags)  # 拆条素材的相关标签
    create_at = models.DateTimeField(auto_now_add=True, db_index=True)
    update_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(default=0, null=False)
    offset = models.IntegerField(default=0, null=False)  # 拆条视频在原视频的位置（毫秒）
    duration = models.IntegerField(default=0, null=False)  # 拆条视频的长度（毫秒）
    file_size = models.IntegerField(default=0, null=False)
    height = models.IntegerField(default=0, null=False)
    video_fragment_url = models.CharField(
        max_length=1024, null=True, default=None)  # 拆条视频的存储位置
    video_fragment_cover_url = models.CharField(
        max_length=1024, null=True, default=None)  # 拆条视频的封面存储位置
    fragment_duration = models.IntegerField(default=0, null=False)  # 拆条视频的实际时长
    fragment_asset_key = models.CharField(
        max_length=64, null=True, default=None)  # 转成素材后的素材asset_key
    desc = models.TextField(null=True, default=None)  # 拆条视频的描述
    title = models.CharField(max_length=256, null=True, default=None)
    deleted = models.BooleanField(null=False, default=False)  # 拆条删除的标记
    profile_id = models.IntegerField(
        null=False, default=0, db_index=True)  # 没用外键是想减少关联性；
    worker_id = models.IntegerField(
        null=False, default=0)  # 用来表示当前切片是否被一个worker正在处理

    @classmethod
    def insert(cls, asset_id, profile_id, offset, duration):
        try:
            vf = cls.objects.create(
                origin_asset_id=asset_id,
                offset=offset,
                duration=duration,
                profile_id=profile_id)
            num = len(
                cls.object.filter(
                    origin_asset_id=asset_id, profile_id=profile_id))
            return dict(
                id=vf.id, asset_id=asset_id, title="片段{}".format(num)), 'ok'
        except Exception as e:
            print(str(e))
            return None, str(e)

    @classmethod
    def update(cls, fragment_id, params):
        """
        修改，删除 fragment都是这个接口
        params is a dirct
        """
        try:
            kwargs = {
                k: v
                for k, v in params.items() if k in [
                    'status', 'offset', 'duration', 'fragment_url', 'desc',
                    'deleted', 'title'
                ]
            }
            if len(kwargs) > 0:
                cls.objects.filter(pk=fragment_id).update(**kwargs)
            # 更新视频标签......
            VideoFragments.update_tags(fragment_id, params.get('tag_ids'))
            return fragment_id, 'ok'
        except Exception as e:
            print(str(e))
            return None, str(e)

    @classmethod
    def update_tags(cls, fragment_id, tag_ids):
        if tag_ids is None or len(tag_ids) == 0:
            return []
        s_ids = ",".join([str(i) for i in tag_ids])
        del_sql = "delete from vtags_videofragments_tags where videofragments_id = {} and tags_id not in ({});".format(
            fragment_id, s_ids)
        with connection.cursor() as cursor:
            cursor.execute(del_sql)
            # 去掉已经存在的ID
            s_sql = "select tags_id from vtags_videofragments_tags where videofragments_id = {} and tags_id not in({});".format(
                fragment_id, s_ids)
            cursor.execute(s_sql)
            r = cursor.fetchone()
            while r is not None:
                if r[0] in tag_ids:
                    tag_ids.remove(r[0])
                r = cursor.fetchone()
        if len(tag_ids) == 0:
            return []
        utags = Tags.objects.filter(id__in=tag_ids)
        if len(utags) == 0:
            return fragment_id, 'ok'
        cls.objects.get(pk=fragment_id).tags.add(*tuple(utags))
        return tag_ids

    @classmethod
    def delete(cls, fragment_id, deleted, tag_ids):
        try:
            if deleted:
                cls.objects.filter(
                    pk=fragment_id, deleted=False).update(deleted=True)
            if tag_ids is not None and len(tag_ids) > 0:
                f = cls.objects.get(pk=fragment_id)
                tags = Tags.objects.filter(id__in=tag_ids)
                for t in tags:
                    f.tags.remove(t)
                f.save()
            return
        except Exception as e:
            print(str(e))
            return None, str(e)

    @classmethod
    def fragments_summary(cls, fragments_ids):
        try:
            records = {}
            asset_ids = set()
            rs = cls.objects.filter(id__in=fragments_ids)
            for r in rs:
                tag_ids = []
                tag_names = []
                tags = r.tags.all()
                for t in tags:
                    tag_ids.append(t.id)
                    tag_names.append(t.name)
                records[r.id] = dict(
                    id=r.id,
                    title=r.title,
                    tag_ids=tag_ids,
                    tag_names=tag_names,
                    desc=r.desc,
                    create_time=r.create_at.strftime("%Y-%m-%d %H:%M:%S"),
                    v_url=r.video_fragment_url,
                    c_url=r.video_fragment_cover_url,
                    asset_id=r.origin_asset_key,
                    offset=r.offset,
                    duration=r.duration,
                    fragment_duration=r.fragment_duration,
                    file_size=r.file_size,
                    resolution='%sP' % r.height if r.height else None,
                    status=cls.STATUS[r.status],
                )
                asset_ids.add(r.origin_asset_key)
            results = []
            for id in fragments_ids:
                r = records.get(id, {})
                results.append(r)
            return results, asset_ids, 'ok'
        except Exception as e:
            print(str(e))
            return None, None, str(e)

    @classmethod
    def filter_by_user(cls, user_ids, tag_ids=None):
        """
        user_ids is a list of profiles
        """
        fragment_ids = []
        utag_ids = set()
        try:
            if not tag_ids:
                rs = cls.objects.filter(
                    profile_id__in=user_ids,
                    deleted=False,
                    status__gt=0).order_by('create_at')
            else:
                rs = cls.objects.filter(
                    profile_id__in=user_ids,
                    tags__id__in=tag_ids,
                    deleted=False,
                    status__gt=0).order_by('create_at')
            # tags = set(tag_ids) if tag_ids else set()
            for r in rs:
                rtags = set([int(t.id) for t in r.tags.all()])
                utag_ids.union(rtags)
                if r.id not in fragment_ids:
                    fragment_ids.append(r.id)
        except Exception as e:
            print(str(e))
        return fragment_ids, utag_ids

    @classmethod
    def search_by_user(cls, user_ids, title, tag_ids=None, start_time=None, end_time=None):
        fragment_ids = []
        if tag_ids is not None:
            tag_ids = set(tag_ids)

        try:
            kwargs = dict(
                profile_id__in=user_ids,
                deleted=False,
                status__gt=0,
            )
            if start_time is not None:
                kwargs['create_at__date__gt'] = datetime.strptime(start_time, '%Y-%m-%d').date()
            if end_time is not None:
                kwargs['create_at__date__lt'] = datetime.strptime(end_time, '%Y-%m-%d').date()
            if tag_ids is not None and len(tag_ids) > 0:
                kwargs['tags__id__in'] = tag_ids
            if title is not None and len(title) > 0:
                kwargs['title__icontains'] = title
            rs = cls.objects.filter(**kwargs).order_by('create_at')
            if tag_ids is None:
                tag_ids = set()
            for r in rs:
                r_tags_ids = [int(t.id) for t in r.tags.all()]
                if len(r_tags_ids) > 0:
                    tag_ids.union(set(r_tags_ids))
                if r.id not in fragment_ids:
                    fragment_ids.append(r.id)
        except Exception as e:
            print(str(e))
        return fragment_ids, tag_ids

    # @classmethod
    # def search_by_user2(cls, user_ids, keywords, tag_ids=None):
    #     fragment_ids = []
    #     asset_ids = set()
    #     try:
    #         if tag_ids is None:
    #             rs = cls.objects.filter(
    #                 profile_id__in=user_ids,
    #                 deleted=False,
    #                 title__icontains=keywords)
    #         else:
    #             rs = cls.objects.filter(
    #                 profile_id__in=user_ids,
    #                 tags__id__in=tag_ids,
    #                 deleted=False,
    #                 title__icontains=keywords)
    #         for r in rs:
    #             fragment_ids.append(r.id)
    #             asset_ids.add(r.asset_id)
    #     except Exception as e:
    #         print(str(e))
    #     return fragment_ids, asset_ids

    @classmethod
    def filter_by_video(cls, asset_id, user_id):
        try:
            fragments = []
            rs = cls.objects.filter(
                origin_asset_key=asset_id, profile_id=user_id,
                deleted=False).order_by('-create_at')
            for r in rs:
                v = dict(
                    id=r.id,
                    asset_id=r.origin_asset_id,
                    asset_key=r.origin_asset_key,
                    create_time=r.create_at.strftime("%Y-%m-%d %H:%M:%S"),
                    update_time=r.update_at.strftime("%Y-%m-%d %H:%M:%S"),
                    desc=r.desc,
                    offset=r.offset,
                    duration=r.duration,
                    status=cls.STATUS[r.status],
                    title=r.title,
                    cover_url=r.video_fragment_cover_url)
                tag_ids = []
                tags = r.tags.all()
                for t in tags:
                    tag_ids.append(t.id)
                v['tag_ids'] = tag_ids
                fragments.append(v)
            return fragments, 'ok'
        except Exception as e:
            print(str(e))
            return None, str(e)

    @classmethod
    def is_any_fragments_spliced(cls, fragments):
        try:
            if not fragments:
                return False
            with connection.cursor() as cursor:
                for fragment in fragments:
                    sql = "select * from vtags_videofragments where videofragments_id={}".format(
                        fragment.id)
                    cursor.execute(sql)
                    r = cursor.fetchone()
                    if r:
                        return True
            return False
        except:
            return False

    @classmethod
    def filter_fragments_by_title(cls, users, tag_ids, title):
        # test
        s = "{}".format(title)
        print(s)
        try:
            where_str = "where vf.profile_id in {} ".format(users)
            print(where_str)
            where_str += "and at.title LIKE '%{}%' ".format(title)
            print(where_str)
            with connection.cursor() as cursor:
                print(users, tag_ids, title)
                if tag_ids:
                    tag_ids = list_to_str(tag_ids)
                    where_str += "and vt.tags_id in {} ".format(tag_ids)
                    print(where_str)
                    sql = """select vf.id 
                        from vtags_videofragments vf
                        left join vtags_videofragments_tags vt on vf.id = vt.videofragments_id
                        left join asset_videoasset at on vf.origin_asset_key=at.asset_key
                        {}
                        group by vf.id
                        order by vf.create_at;""".format(where_str)
                else:
                    sql = """select vf.id 
                        from vtags_videofragments vf
                        left join vtags_videofragments_tags vt on vf.id = vt.videofragments_id
                        left join asset_videoasset at on vf.origin_asset_key=at.asset_key
                        {}
                        group by vf.id
                        order by vf.create_at;""".format(where_str)
                print(sql)
                cursor.execute(sql)
                frag_ids = []
                r = cursor.fetchone()
                while r is not None:
                    frag_ids.append(r[0])
                    r = cursor.fetchone()
                return frag_ids
        except Exception as e:
            print(str(e))
            return []

    @classmethod
    def filter_fragments_by_tag_name(cls, users, tag_ids, tag_name):
        try:
            with connection.cursor() as cursor:
                append_tag_name_sql = "select id from vtags_tags where name LIKE '%{}%'".format(
                    tag_name)
                cursor.execute(append_tag_name_sql)
                rs = cursor.fetchall()
                if not rs:
                    return []
                else:
                    r = [int(c[0]) for c in rs]
                if tag_ids is None:
                    tag_ids = list(set(r)) if r else []
                else:
                    if r:
                        tag_ids.extend(r)
                    tag_ids = list(set(tag_ids)) if r else tag_ids
                tag_ids = str(
                    tuple(tag_ids)) if len(tag_ids) > 1 else "({})".format(
                    tag_ids[0])

                if tag_ids:
                    # tags = [int(tag) for tag in tag_ids] if len(tag_ids)>1 else tag_ids
                    sql = """select vf.id 
                             from vtags_videofragments vf
                             left join vtags_videofragments_tags vt on vf.id = vt.videofragments_id
                             where vf.profile_id in {} and vt.tags_id in {}
                             group by vf.id
                             order by vf.create_at;""".format(users, tag_ids)
                    cursor.execute(sql)
                    r = cursor.fetchone()
                    frag_ids = []
                    while r is not None:
                        frag_ids.append(r[0])
                        r = cursor.fetchone()
                    return list(set(frag_ids))
                else:
                    sql = """select vf.id 
                             from vtags_videofragments vf
                             left join vtags_videofragments_tags vt on vf.id = vt.videofragments_id
                             where vf.profile_id in {} 
                             group by vf.id
                             order by vf.create_at;""".format(users)
                    cursor.execute(sql)
                    r = cursor.fetchone()
                    frag_ids = []
                    while r is not None:
                        frag_ids.append(r[0])
                        r = cursor.fetchone()
                    return list(set(frag_ids))

        except Exception as e:
            print(str(e))
            return []

    @classmethod
    def filter_fragments_by_sql(cls, user_ids, tag_name, title, tag_ids=None):
        user_ids = [int(u) for u in user_ids]
        if len(user_ids) == 1:
            users = "({})".format(user_ids[0])
        else:
            users = str(tuple(user_ids))
        if title:
            return cls.filter_fragments_by_title(users, tag_ids, title)
        if tag_name:
            return cls.filter_fragments_by_tag_name(users, tag_ids, tag_name)

    @classmethod
    def get_fragments_status(cls, fragment_ids):
        try:
            results = []
            rs = cls.objects.filter(pk__in=json.loads(fragment_ids))
            for r in rs:
                results.append(
                    dict(
                        id=r.id,
                        status=cls.STATUS[r.status],
                        resolution='%sP' % r.height if r.height else None,
                        file_size=r.file_size,
                        c_url=r.video_fragment_cover_url,
                        v_url=r.video_fragment_url))
            return results, 'ok'
        except Exception as e:
            print(str(e))
            return None, str(e)

    @classmethod
    def lock_fragments_status(cls, status, worker_id, limits=10):
        try:
            with transaction.atomic():
                # 获取worker_id 相等，status = status+1到记录，这些记录是上次获取到正在执行的记录；
                rs = cls.objects.filter(
                    status=status, worker_id=0).order_by('id')[:limits]
                for r in rs:
                    r.worker_id = worker_id
                    r.status = status + 1  # 一般状态 +1 都是上一个状态的进行时.....
                    r.save()
                return rs
        except Exception as e:
            print(str(e))
        return []

    @classmethod
    def free_fragments_status(cls, id, next_status, worker_id):
        try:
            n = cls.objects.filter(
                pk=id, worker_id=worker_id).update(
                status=next_status, worker_id=0)
            return n
        except Exception as e:
            str(e)
            return 0




