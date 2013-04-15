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
package au.edu.monash.merc.capture.struts2.action;

import au.edu.monash.merc.capture.config.ConfigSettings;
import au.edu.monash.merc.capture.domain.*;
import au.edu.monash.merc.capture.dto.InheritPermissionBean;
import au.edu.monash.merc.capture.dto.PermissionBean;
import au.edu.monash.merc.capture.dto.page.Pagination;
import au.edu.monash.merc.capture.identifier.IdentifierService;
import au.edu.monash.merc.capture.service.DMService;
import au.edu.monash.merc.capture.util.CaptureUtil;
import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;

import javax.annotation.PostConstruct;
import java.util.Date;
import java.util.List;

public class DMCoreAction extends BaseAction {

    protected boolean collectionError;

    protected Pagination<Collection> pagination;

    protected Collection collection;

    protected List<Dataset> datasets;

    @Autowired
    protected DMService dmService;

    @Autowired
    protected IdentifierService pidService;

    private String viewColDetailLink;

    private String showColEditLink;

    private String deleteColLink;

    private String permissionLink;

    private String downloadDatasetLink;

    private String deleteDatasetLink;

    private String viewDatasetLink;

    private String andsMdRegLink;

    private boolean sharingData;

    protected String viewType;

    protected PermissionBean permissionBean;

    private Logger logger = Logger.getLogger(this.getClass().getName());

    //citation info
    protected String publisher;

    @PostConstruct
    public void init() {
        this.publisher = this.configSetting.getPropValue(ConfigSettings.ANDS_RIFCS_REG_GROUP_NAME);
    }

    protected void populateLinksInUsrCollection() {
        showColEditLink = ActConstants.SHOW_COLLECTION_EDIT_ACTION;
        deleteColLink = ActConstants.COLLECTION_DELETE_ACTION;
        downloadDatasetLink = ActConstants.DATASET_EXPORT_ACTION;
        deleteDatasetLink = ActConstants.DATASET_DELETE_ACTION;
        viewDatasetLink = ActConstants.DATASET_VIEWDATA_ACTION;
        permissionLink = ActConstants.SET_COLLECTION_PERMISSION_ACTION;
        andsMdRegLink = ActConstants.ANDS_MD_REG_SHOW_ACTION;
    }

    protected void populateLinksInPubCollection() {
        downloadDatasetLink = ActConstants.PUB_DATASET_EXPORT_ACTION;
        viewDatasetLink = ActConstants.PUB_DATASET_VIEWDATA_ACTION;
    }

    protected void setViewColDetailActionName(String viewColDetailActionName) {
        this.viewColDetailLink = viewColDetailActionName;
    }

    protected String genShortDesc(String description) {

        if (!StringUtils.isBlank(description)) {
            int total = description.trim().length();
            if (total <= ActConstants.BRIEF_DESCRIPTION_MAX_LENGTH) {
                return description.trim();
            } else {
                String shortdesc = StringUtils.substring(description.trim(), 0, ActConstants.BRIEF_DESCRIPTION_MAX_LENGTH - 1);
                return StringUtils.substringBeforeLast(shortdesc, " ") + " ... ";
            }
        } else {
            return description;
        }
    }

    protected PermissionBean checkPermission(long collectionId, long ownerId) {
        // retrieve the logged in user if any
        user = retrieveLoggedInUser();

        //anonymous user
        if (user == null) {
            Permission anonymoutPerm = this.dmService.getAnonymousCollectionPermission(collectionId);
            PermissionBean pmBean = copyPermissionToPermissionBean(anonymoutPerm);
            return pmBean;
        }

        //owner of the collection
        if (user.getId() == ownerId) {
            PermissionBean pmBean = new PermissionBean();
            pmBean.setFullPermissions();
            return pmBean;
        }

        //admin
        if (user != null && (user.getUserType() == UserType.ADMIN.code() || (user.getUserType() == UserType.SUPERADMIN.code()))) {
            // create a new permissions.
            PermissionBean pmBean = new PermissionBean();
            pmBean.setFullPermissions();
            return pmBean;
        }

        //user
        Permission userPerm = this.dmService.getUserCollectionPermission(collectionId, user.getId());
        if (userPerm == null) {
            InheritPermissionBean inheritPmBean = this.dmService.getUserInheritPermission(collectionId, user.getId());
            PermissionBean pmBean = copyInheritPermissionToPermissionBean(inheritPmBean);
            return pmBean;
        } else {
            PermissionBean pmBean = copyPermissionToPermissionBean(userPerm);
            return pmBean;
        }
    }

    protected PermissionBean copyPermissionToPermissionBean(Permission permission) {
        PermissionBean pmBean = new PermissionBean();
        if (permission != null) {
            pmBean.setId(permission.getId());
            pmBean.setUid(permission.getPermForUser().getId());
            pmBean.setUserName(permission.getPermForUser().getDisplayName());
            int viewAllowed = permission.getViewAllowed();
            if (viewAllowed == 0) {
                pmBean.setViewAllowed(false);
            } else {
                pmBean.setViewAllowed(true);
            }

            int importAllowed = permission.getImportAllowed();
            if (importAllowed == 0) {
                pmBean.setImportAllowed(false);
            } else {
                pmBean.setImportAllowed(true);
            }

            int exportAllowed = permission.getExportAllowed();
            if (exportAllowed == 0) {
                pmBean.setExportAllowed(false);
            } else {
                pmBean.setExportAllowed(true);
            }

            int mdRegAllowed = permission.getMdRegisterAllowed();
            if (mdRegAllowed == 0) {
                pmBean.setMdRegAllowed(false);
            } else {
                pmBean.setMdRegAllowed(true);
            }

            int racAllowed = permission.getRacAllowed();
            if (racAllowed == 0) {
                pmBean.setRacAllowed(false);
            } else {
                pmBean.setRacAllowed(true);
            }

            int updateAllowed = permission.getUpdateAllowed();
            if (updateAllowed == 0) {
                pmBean.setUpdateAllowed(false);
            } else {
                pmBean.setUpdateAllowed(true);
            }

            int deleteAllowed = permission.getDeleteAllowed();
            if (deleteAllowed == 0) {
                pmBean.setDeleteAllowed(false);
            } else {
                pmBean.setDeleteAllowed(true);
            }

            int acAllowed = permission.getAcAllowed();
            if (acAllowed == 0) {
                pmBean.setAcAllowed(false);
            } else {
                pmBean.setAcAllowed(true);
            }
        }
        return pmBean;
    }

    private PermissionBean copyInheritPermissionToPermissionBean(InheritPermissionBean permission) {
        PermissionBean pmBean = new PermissionBean();
        if (permission != null) {
            pmBean.setUid(permission.getPermUserId());
            int viewAllowed = permission.getViewAllowed();
            if (viewAllowed == 0) {
                pmBean.setViewAllowed(false);
            } else {
                pmBean.setViewAllowed(true);
            }
            int updateAllowed = permission.getUpdateAllowed();
            if (updateAllowed == 0) {
                pmBean.setUpdateAllowed(false);
            } else {
                pmBean.setUpdateAllowed(true);
            }

            int importAllowed = permission.getImportAllowed();
            if (importAllowed == 0) {
                pmBean.setImportAllowed(false);
            } else {
                pmBean.setImportAllowed(true);
            }

            int exportAllowed = permission.getExportAllowed();
            if (exportAllowed == 0) {
                pmBean.setExportAllowed(false);
            } else {
                pmBean.setExportAllowed(true);
            }

            int deleteAllowed = permission.getDeleteAllowed();
            if (deleteAllowed == 0) {
                pmBean.setDeleteAllowed(false);
            } else {
                pmBean.setDeleteAllowed(true);
            }

            int mdRegAllowed = permission.getMdRegisterAllowed();
            if (mdRegAllowed == 0) {
                pmBean.setMdRegAllowed(false);
            } else {
                pmBean.setMdRegAllowed(true);
            }
            int acAllowed = permission.getAcAllowed();
            if (acAllowed == 0) {
                pmBean.setAcAllowed(false);
            } else {
                pmBean.setAcAllowed(true);
            }

            int racAllowed = permission.getRacAllowed();
            if (racAllowed == 0) {
                pmBean.setRacAllowed(false);
            } else {
                pmBean.setRacAllowed(true);
            }
        }
        return pmBean;
    }

    protected void setupFullPermissions() {
        permissionBean = new PermissionBean();
        permissionBean.setFullPermissions();
    }

    protected void retrieveCollection() {
        // get the current collection.
        collection = this.dmService.getCollection(collection.getId(), collection.getOwner().getId());
        String textAreaDesc = collection.getDescription();
        String htmlDesc = nlToBr(textAreaDesc);
        collection.setDescription(htmlDesc);
        // populate the collectionlinks
        populateLinksInUsrCollection();
    }

    protected void retrieveAllDatasets() {
        datasets = this.dmService.getDatasetByCollectionIdUsrId(collection.getId(), collection.getOwner().getId());
    }

    protected void recordActionAuditEvent(AuditEvent event) {
        try {
            this.dmService.saveAuditEvent(event);
        } catch (Exception e) {
            // if can't persist the audit event, just log the exception, and let the other action finish
            logger.error("Failed to persist the audit event, " + e.getMessage());
            logger.error(event.getEvent() + " , operated by " + event.getOperator().getDisplayName() + ", audit event owned by "
                    + event.getEventOwner().getDisplayName());
        }
    }

    protected Date normalizeDate(Date date) {
        String endtimeStr = CaptureUtil.dateToYYYYMMDDStr(date);
        Date newEndTime = CaptureUtil.formatDate(endtimeStr + ActConstants.LAST_TIME_OF_DAY);
        return newEndTime;
    }

    public boolean isCollectionError() {
        return collectionError;
    }

    public void setCollectionError(boolean collectionError) {
        this.collectionError = collectionError;
    }

    public Pagination<Collection> getPagination() {
        return pagination;
    }

    public void setPagination(Pagination<Collection> pagination) {
        this.pagination = pagination;
    }

    public Collection getCollection() {
        return collection;
    }

    public void setCollection(Collection collection) {
        this.collection = collection;
    }

    public List<Dataset> getDatasets() {
        return datasets;
    }

    public void setDatasets(List<Dataset> datasets) {
        this.datasets = datasets;
    }

    public void setDmService(DMService dmService) {
        this.dmService = dmService;
    }

    public void setPidService(IdentifierService pidService) {
        this.pidService = pidService;
    }

    public String getViewColDetailLink() {
        return viewColDetailLink;
    }

    public void setViewColDetailLink(String viewColDetailLink) {
        this.viewColDetailLink = viewColDetailLink;
    }

    public String getDownloadDatasetLink() {
        return downloadDatasetLink;
    }

    public String getShowColEditLink() {
        return showColEditLink;
    }

    public void setShowColEditLink(String showColEditLink) {
        this.showColEditLink = showColEditLink;
    }

    public String getDeleteColLink() {
        return deleteColLink;
    }

    public void setDeleteColLink(String deleteColLink) {
        this.deleteColLink = deleteColLink;
    }

    public void setDownloadDatasetLink(String downloadDatasetLink) {
        this.downloadDatasetLink = downloadDatasetLink;
    }

    public String getDeleteDatasetLink() {
        return deleteDatasetLink;
    }

    public void setDeleteDatasetLink(String deleteDatasetLink) {
        this.deleteDatasetLink = deleteDatasetLink;
    }

    public String getViewDatasetLink() {
        return viewDatasetLink;
    }

    public void setViewDatasetLink(String viewDatasetLink) {
        this.viewDatasetLink = viewDatasetLink;
    }

    public String getPermissionLink() {
        return permissionLink;
    }

    public void setPermissionLink(String permissionLink) {
        this.permissionLink = permissionLink;
    }

    public String getAndsMdRegLink() {
        return andsMdRegLink;
    }

    public void setAndsMdRegLink(String andsMdRegLink) {
        this.andsMdRegLink = andsMdRegLink;
    }

    public boolean isSharingData() {
        return sharingData;
    }

    public void setSharingData(boolean sharingData) {
        this.sharingData = sharingData;
    }

    public String getViewType() {
        return viewType;
    }

    public void setViewType(String viewType) {
        this.viewType = viewType;
    }

    public PermissionBean getPermissionBean() {
        return permissionBean;
    }

    public void setPermissionBean(PermissionBean permissionBean) {
        this.permissionBean = permissionBean;
    }

    public String getPublisher() {
        return publisher;
    }

    public void setPublisher(String publisher) {
        this.publisher = publisher;
    }
}
