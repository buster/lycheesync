# -*- coding: utf-8 -*-

import MySQLdb
import datetime
import traceback


class LycheeDAO:
    """
    Implements linking with Lychee DB
    """

    db = None
    conf = None
    albumslist = {}

    def __init__(self, conf):
        """
        Takes a dictionnary of conf as input
        """

        self.conf = conf
        self.db = MySQLdb.connect(host=self.conf["dbHost"],
                                  user=self.conf["dbUser"],
                                  passwd=self.conf["dbPassword"],
                                  db=self.conf["db"])

        if self.conf["dropdb"]:
            self.dropAll()

        self.loadAlbumList()

    def getAlbumMinMaxIds(self):
        """
        returns min, max album ids
        """
        min_album_query = "select min(id) from lychee_albums"
        max_album_query = "select max(id) from lychee_albums"
        try:
            min = -1
            max = -1
            cur = self.db.cursor()
            cur.execute(min_album_query)
            rows = cur.fetchall()
            for row in rows:
                min = row[0]

            cur.execute(max_album_query)
            rows = cur.fetchall()
            for row in rows:
                max = row[0]

            if self.conf["verbose"]:
                print "INFO min, max album id: ", min, " to ", max

            res = min, max
        except Exception:
            res = -1, -1
            print "getAlbumMinMaxIds", Exception
            traceback.print_exc()
        finally:
            return res

    def updateAlbumDate(self, albumid, newdate):
        """
        Update album date to an arbitrary date
        """
        res = True
        qry = "update lychee_albums set sysdate= '" + str(newdate) + "' where id=" + str(albumid)
        try:
            cur = self.db.cursor()
            cur.execute(qry)
            self.db.commit()
            if self.conf["verbose"]:
                print "INFO album id sysdate changed to: ", newdate
        except Exception:
            res = False
            print "updateAlbumDate", Exception
            traceback.print_exc()
        finally:
            return res




    def changeAlbumId(self, oldid, newid):
        """
        Change albums id based on album titles (to affect display order)
        """
        res = True
        photo_query = "update lychee_photos set album = " + str(newid) + " where album = " + str(oldid)
        album_query = "update lychee_albums set id = " + str(newid) + " where id = " + str(oldid)
        try:
            cur = self.db.cursor()
            cur.execute(photo_query)
            cur.execute(album_query)
            self.db.commit()
            if self.conf["verbose"]:
                print "INFO album id changed: ", oldid, " to ", newid
        except Exception:
            res = False
            print "changeAlbumId", Exception
            print "ERROR album id changed: ", oldid, " to ", newid
            traceback.print_exc()
        finally:
            return res

    def loadAlbumList(self):
        """
        retrieve all albums in a dictionnary key=title value=id
        and put them in self.albumslist
        returns self.albumlist
        """
        #Load album list
        cur = self.db.cursor()
        cur.execute("SELECT title,id from lychee_albums")
        rows = cur.fetchall()
        for row in rows:
            self.albumslist[row[0]] = row[1]

        if self.conf['verbose']:
            print "INFO album list in db:", self.albumslist
        return self.albumslist

    def albumExists(self, album):
        """
        Check if an album exists based on its name
        Parameters: an album properties list. At least the name should be specified
        Returns None or the albumid if it exists
        """

        if album['name'] in self.albumslist.keys():
            return self.albumslist[album['name']]
        else:
            return None

    def photoExists(self, photo):
        """
        Check if an album exists based on its original name
        Parameter:
        - photo: a valid LycheePhoto object
        Returns a boolean
        """
        res = False
        try:
            query = ("select * from lychee_photos where album=" + str(photo.albumid) +
                     " and import_name = '" + photo.originalname + "'")
            cur = self.db.cursor()
            cur.execute(query)
            row = cur.fetchall()
            if len(row) != 0:
                res = True

        except Exception:
            print "ERROR photoExists:", photo.srcfullpath, "won't be added to lychee"
            traceback.print_exc()
            res = True
        finally:
            return res

    def createAlbum(self, album):
        """
        Creates an album
        Parameter:
        - album: the album properties list, at least the name should be specified
        Returns the created albumid or None
        """
        album['id'] = None
        query = ("insert into lychee_albums (title, sysdate, public, password) values ('" +
                 album['name'] + "','" + datetime.date.today().isoformat() + "'," +
                 str(self.conf["publicAlbum"]) + ", NULL)")
        try:
            cur = self.db.cursor()
            cur.execute(query)
            self.db.commit()

            #cur.execute(query, (name, self.conf["publicAlbum"]))
            query = "select id from lychee_albums where title='" + album['name'] + "'"
            cur.execute(query)
            row = cur.fetchone()
            self.albumslist['name'] = row[0]
            album['id'] = row[0]
            if self.conf["verbose"]:
                print "INFO album created:", album

        except Exception:
            print "createAlbum", Exception
            traceback.print_exc()
            album['id'] = None
        finally:
            return album['id']

    def eraseAlbum(self, album):
        """
        Deletes all photos of an album but don't delete the album itself
        Parameters:
        - album: the album properties list to erase.  At least its id must be provided
        Return list of the erased photo url
        """
        res = []
        query = "delete from lychee_photos where album = " + str(album['id']) + ''
        selquery = "select url from lychee_photos where album = " + str(album['id']) + ''
        try:
            cur = self.db.cursor()
            cur.execute(selquery)
            rows = cur.fetchall()
            for row in rows:
                res.append(row[0])
            cur.execute(query)
            self.db.commit()
            if self.conf["verbose"]:
                print "INFO album erased: ", album
        except Exception:
            print "eraseAlbum", Exception
            traceback.print_exc()
        finally:
            return res

    def listAllPhoto(self):
        """
        Lists all photos in leeche db (used to delete all files)
        Return a photo url list
        """
        res = []
        selquery = "select url from lychee_photos"
        try:
            cur = self.db.cursor()
            cur.execute(selquery)
            rows = cur.fetchall()
            for row in rows:
                res.append(row[0])
        except Exception:
            print "listAllPhoto", Exception
            traceback.print_exc()
        finally:
            return res

    def addFileToAlbum(self, photo):
        """
        Add a photo to an album
        Parameter:
        - photo: a valid LycheePhoto object
        Returns a boolean
        """
        res = True
        #print photo
        query = ("insert into lychee_photos " +
                 "(id, url, public, type, width, height, " +
                 "size,  sysdate, systime, star, " +
                 "thumbUrl, album,iso, aperture, make, " +
                 "model, shutter, focal, takedate, " +
                 "taketime, import_name, description, title) " +
                 "values " +
                 "({}, '{}', {}, '{}' ,{}, {}, " +
                 "'{}','{}', '{}', {}, " +
                 "'{}',{}, '{}','{}','{}', " +
                 "'{}', '{}', '{}', '{}', " +
                 "'{}', '{}', '{}', '{}')"
                 ).format(photo.id, photo.url, self.conf["publicAlbum"], photo.type, photo.width, photo.height,
                          photo.size, photo.sysdate, photo.systime, photo.star,
                          photo.thumbUrl, photo.albumid, photo.exif.iso, photo.exif.aperture, photo.exif.make,
                          photo.exif.model, photo.exif.shutter, photo.exif.focal, photo.exif.takedate,
                          photo.exif.taketime, photo.originalname, photo.description, photo.originalname)
        #print query

        try:
            cur = self.db.cursor()
            res = cur.execute(query)
            self.db.commit()
        except Exception:
            print "addFileToAlbum", Exception
            traceback.print_exc()
            res = False
        finally:
            return res


    def reinitAlbumAutoIncrement(self):

        min, max = self.getAlbumMinMaxIds()
        qry = "alter table lychee_albums AUTO_INCREMENT=" + str(max+1)
        try:
            cur = self.db.cursor()
            cur.execute(qry)
            self.db.commit()
            if self.conf['verbose']:
                print "INFO: reinit auto increment to", str(max+1)
        except Exception:
            print "reinitAlbumAutoIncrement", Exception
            traceback.print_exc()

    def close(self):
        """
        Close DB Connection
        Returns nothing
        """
        if self.db:
            self.db.close()

    def dropAll(self):
        """
        Drop all albums and photos from DB
        Returns nothing
        """
        try:
            cur = self.db.cursor()
            cur.execute("delete from lychee_albums")
            cur.execute("delete from lychee_photos")
            self.db.commit()
        except Exception:
            print "dropAll", Exception
            traceback.print_exc()
