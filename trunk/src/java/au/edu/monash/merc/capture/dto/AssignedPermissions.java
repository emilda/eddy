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

import java.util.ArrayList;
import java.util.List;

import au.edu.monash.merc.capture.domain.CPermission;
import au.edu.monash.merc.capture.domain.Permission;

public class AssignedPermissions {

    //TODO: to be removed
    private List<Permission> permissionsNew = new ArrayList<Permission>();

    private List<Permission> permissionsUpdate = new ArrayList<Permission>();

    private List<Long> deletePermsIds = new ArrayList<Long>();

    public List<Permission> getPermissionsNew() {
        return permissionsNew;
    }

    public void setPermissionsNew(List<Permission> permissionsNew) {
        this.permissionsNew = permissionsNew;
    }

    public List<Permission> getPermissionsUpdate() {
        return permissionsUpdate;
    }

    public void setPermissionsUpdate(List<Permission> permissionsUpdate) {
        this.permissionsUpdate = permissionsUpdate;
    }

    public List<Long> getDeletePermsIds() {
        return deletePermsIds;
    }

    public void setDeletePermsIds(List<Long> deletePermsIds) {
        this.deletePermsIds = deletePermsIds;
    }

    private long collectionId;

    private CPermission anonymousPerm;

    private CPermission allRegisteredPerm;

    private List<CPermission> registeredUserPerms = new ArrayList<CPermission>();

    public long getCollectionId() {
        return collectionId;
    }

    public void setCollectionId(long collectionId) {
        this.collectionId = collectionId;
    }

    public CPermission getAnonymousPerm() {
        return anonymousPerm;
    }

    public void setAnonymousPerm(CPermission anonymousPerm) {
        this.anonymousPerm = anonymousPerm;
    }

    public CPermission getAllRegisteredPerm() {
        return allRegisteredPerm;
    }

    public void setAllRegisteredPerm(CPermission allRegisteredPerm) {
        this.allRegisteredPerm = allRegisteredPerm;
    }

    public List<CPermission> getRegisteredUserPerms() {
        return registeredUserPerms;
    }

    public void setRegisteredUserPerms(List<CPermission> registeredUserPerms) {
        this.registeredUserPerms = registeredUserPerms;
    }

    public void setRegisteredUserPerm(CPermission permission) {
        this.registeredUserPerms.add(permission);
    }
}
