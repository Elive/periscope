# -*- coding: utf-8 -*-

#   This file is part of periscope.
#   Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import zipfile, os, urllib.request, urllib.error, urllib.parse, urllib.request, urllib.parse, urllib.error, logging, traceback, http.client, re
from bs4 import BeautifulSoup

from . import SubtitleDatabase

log = logging.getLogger(__name__)

LANGUAGES = {"English (US)" : "en",
             "English (UK)" : "en",
             "English" : "en",
             "French" : "fr",
             "Brazilian" : "pt-br",
             "Portuguese" : "pt",
             "Español (Latinoamérica)" : "es",
             "Español (España)" : "es",
             "Español" : "es",
             "Italian" : "it",
             "Català" : "ca"}

class Subtitulos(SubtitleDatabase.SubtitleDB):
    url = "http://www.subtitulos.es"
    site_name = "Subtitulos"

    def __init__(self, config, cache_folder_path):
        super(Subtitulos, self).__init__(langs=None,revertlangs=LANGUAGES)
        #http://www.subtitulos.es/dexter/4x01
        self.host = "http://www.subtitulos.es"
        self.release_pattern = re.compile("Versi&oacute;n (.+) ([0-9]+).([0-9])+ megabytes")
        

    def process(self, filepath, langs):
        ''' main method to call on the plugin, pass the filename and the wished 
        languages and it will query the subtitles source '''
        fname = str(self.getFileName(filepath).lower())
        guessedData = self.guessFileData(fname)
        if guessedData['type'] == 'tvshow':
            subs = self.query(guessedData['name'], guessedData['season'], guessedData['episode'], guessedData['teams'], langs)
            return subs
        else:
            return []
    
    def query(self, name, season, episode, teams, langs=None):
        ''' makes a query and returns info (link, lang) about found subtitles'''
        sublinks = []
        name = name.lower().replace(" ", "-")
        searchurl = "%s/%s/%sx%s" %(self.host, name, season, episode)
        content = self.downloadContent(searchurl, 10)
        if not content:
            return sublinks
        
        soup = BeautifulSoup(content)
        for subs in soup("div", {"id":"version"}):
            version = subs.find("p", {"class":"title-sub"})
            subteams = self.release_pattern.search("%s"%version.contents[1]).group(1).lower()            
            teams = set(teams)
            subteams = self.listTeams([subteams], [".", "_", " ", "/"])
            
            log.debug("Team from website: %s" %subteams)
            log.debug("Team from file: %s" %teams)

            nexts = subs.findAll("ul", {"class":"sslist"})
            for lang_html in nexts:
                langLI = lang_html.findNext("li",{"class":"li-idioma"} )
                lang = self.getLG(langLI.find("strong").contents[0].string.strip())
        
                statusLI = lang_html.findNext("li",{"class":"li-estado green"} )
                if statusLI == None:
                    continue
                else:
                    status = statusLI.contents[0].string.strip()

                class_object = statusLI.findNext("span", {"class":"descargar green"})
                
                if not class_object:
                    continue
                
                link = class_object.find("a")["href"]
                if status == "Completado" and subteams.issubset(teams) and (not langs or lang in langs) :
                    result = {}
                    result["release"] = "%s.S%.2dE%.2d.%s" %(name.replace("-", ".").title(), int(season), int(episode), '.'.join(subteams))
                    result["lang"] = lang
                    result["link"] = link
                    result["page"] = searchurl
                    sublinks.append(result)
                
        return sublinks
        
    def listTeams(self, subteams, separators):
        teams = []
        for sep in separators:
            subteams = self.splitTeam(subteams, sep)
        log.debug(subteams)
        return set(subteams)
    
    def splitTeam(self, subteams, sep):
        teams = []
        for t in subteams:
            teams += t.split(sep)
        return teams

    def createFile(self, subtitle, lang_in_name=False):
        '''pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file'''
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        if lang_in_name: srtbasefilename += "." + subtitle["lang"]
        srtfilename = srtbasefilename +".srt"
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def downloadFile(self, url, filename):
        ''' Downloads the given url to the given filename '''
        req = urllib.request.Request(url, headers={'Referer' : url, 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'})
        
        f = urllib.request.urlopen(req)
        dump = open(filename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()
