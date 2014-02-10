/*
 * Copyright (c) 2010-2011, Monash e-Research Centre
 * (Monash University, Australia)
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 * 	* Redistributions of source code must retain the above copyright
 * 	  notice, this list of conditions and the following disclaimer.
 * 	* Redistributions in binary form must reproduce the above copyright
 * 	  notice, this list of conditions and the following disclaimer in the
 * 	  documentation and/or other materials provided with the distribution.
 * 	* Neither the name of the Monash University nor the names of its
 * 	  contributors may be used to endorse or promote products derived from
 * 	  this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
package au.edu.monash.merc.capture.dto;

import java.io.Serializable;

public class PermissionBean implements Serializable {

    private long id;

    private long uid;

    private String userName;

    private boolean viewAllowed;

    private boolean updateAllowed;

    private boolean importAllowed;

    private boolean exportAllowed;

    private boolean deleteAllowed;

    private boolean mdRegAllowed;

    private boolean acAllowed;

    private boolean racAllowed;

    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    public long getUid() {
        return uid;
    }

    public void setUid(long uid) {
        this.uid = uid;
    }

    public String getUserName() {
        return userName;
    }

    public void setUserName(String userName) {
        this.userName = userName;
    }

    public boolean isViewAllowed() {
        return viewAllowed;
    }

    public void setViewAllowed(boolean viewAllowed) {
        this.viewAllowed = viewAllowed;
    }

    public boolean isUpdateAllowed() {
        return updateAllowed;
    }

    public void setUpdateAllowed(boolean updateAllowed) {
        this.updateAllowed = updateAllowed;
    }

    public boolean isImportAllowed() {
        return importAllowed;
    }

    public void setImportAllowed(boolean importAllowed) {
        this.importAllowed = importAllowed;
    }

    public boolean isExportAllowed() {
        return exportAllowed;
    }

    public void setExportAllowed(boolean exportAllowed) {
        this.exportAllowed = exportAllowed;
    }

    public boolean isDeleteAllowed() {
        return deleteAllowed;
    }

    public void setDeleteAllowed(boolean deleteAllowed) {
        this.deleteAllowed = deleteAllowed;
    }

    public boolean isMdRegAllowed() {
        return mdRegAllowed;
    }

    public void setMdRegAllowed(boolean mdRegAllowed) {
        this.mdRegAllowed = mdRegAllowed;
    }

    public boolean isAcAllowed() {
        return acAllowed;
    }

    public void setAcAllowed(boolean acAllowed) {
        this.acAllowed = acAllowed;
    }

    public boolean isRacAllowed() {
        return racAllowed;
    }

    public void setRacAllowed(boolean racAllowed) {
        this.racAllowed = racAllowed;
    }

    public void setFullPermissions() {
        this.viewAllowed = true;
        this.updateAllowed = true;
        this.importAllowed = true;
        this.exportAllowed = true;
        this.deleteAllowed = true;
        this.mdRegAllowed = true;
        this.acAllowed = true;
        this.racAllowed = true;
    }

    public boolean isNonePerm() {
        if (!this.importAllowed && !this.exportAllowed && !this.racAllowed && !this.updateAllowed && !this.deleteAllowed && !this.acAllowed) {
            return true;
        } else {
            return false;
        }
    }
}
