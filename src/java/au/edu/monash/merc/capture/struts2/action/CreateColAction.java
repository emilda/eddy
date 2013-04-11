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

import au.edu.monash.merc.capture.common.CoverageType;
import au.edu.monash.merc.capture.common.SpatialValue;
import au.edu.monash.merc.capture.config.ConfigSettings;
import au.edu.monash.merc.capture.domain.*;
import au.edu.monash.merc.capture.util.CaptureUtil;
import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Controller;

import java.io.File;
import java.util.ArrayList;
import java.util.Date;
import java.util.GregorianCalendar;
import java.util.List;

/**
 * @author simonyu
 * @version 1.0
 * @since v1.0
 */
@Scope("prototype")
@Controller("data.createColAction")
public class CreateColAction extends DMCoreAction {

    private boolean mdRegEnabled;

    private boolean globalCoverage;

    private Logger logger = Logger.getLogger(this.getClass().getName());

    /**
     * Show create collection action
     *
     * @return a String represents SUCCESS or ERROR.
     */
    public String showCreateCollection() {
        try {
            user = retrieveLoggedInUser();
        } catch (Exception e) {
            logger.error(e.getMessage());
            addActionError(getText("failed.to.show.create.collection.page"));
            setNavForShowExc();
            return INPUT;
        }
        return SUCCESS;
    }

    private void setNavForShowExc() {
        // set the new page title after successful creating a new collection.
        String startNav = getText("mycollection.nav.label.name");
        String startNavLink = ActConstants.USER_LIST_COLLECTION_ACTION;
        String secondNav = getText("create.new.collection");
        String secondNavLink = null;
        setPageTitle(startNav, secondNav + " Error");
        navigationBar = generateNavLabel(startNav, startNavLink, secondNav, secondNavLink, null, null);
    }

    /**
     * Create a new collection
     *
     * @return a String represents SUCCESS or ERROR.
     */
    public String createCollection() {
        // any root path error. directly return the error to front input page.
        if (!checkDataStorePath()) {
            return INPUT;
        }

        try {
            // retrieve logged in user from database
            user = retrieveLoggedInUser();
            // check the collection name
            String colName = collection.getName();
            if (this.dmService.checkCollectionNameExisted(colName)) {
                addActionError(getText("collection.name.already.existed"));
                return INPUT;
            }
            String dataStorePath = configSetting.getPropValue(ConfigSettings.DATA_STORE_LOCATION);

            String userPath = ActConstants.DATA_STORE_USER_ROOT_PREFIX + user.getId();
            // generate the collection file identifier for file system
            String coFileId = CaptureUtil.generateIdBasedOnTimeStamp();
            // generate the uuid for this collection
            String uuidKey = pidService.genUUIDWithPrefix();
            collection.setUniqueKey(uuidKey);

            // construct the file store location
            String colRelPath = File.separator + userPath + File.separator + coFileId;
            collection.setDirPathName(colRelPath);
            Date date = GregorianCalendar.getInstance().getTime();
            collection.setCreatedTime(date);
            collection.setModifiedTime(date);
            String briefDesc = genShortDesc(collection.getDescription());
            collection.setBriefDesc(briefDesc);

            // set the todate into 23:59:59;
            Date todate = collection.getDateTo();
            if (todate != null) {
                collection.setDateTo(normalizeDate(todate));
            }

            // set the collection owner
            collection.setOwner(user);
            // set collection modified by some user, in this case is an owner user
            collection.setModifiedByUser(user);
            //check the location
            String spatialType = null;
            String spatialValue = null;
            if (globalCoverage) {
                spatialType = CoverageType.GLOBAL.type();
                spatialValue = SpatialValue.GLOBAL.value();
            } else {
                Location alocation = collection.getLocation();
                String spValue = alocation.getSpatialCoverage();
                // check the spatial coverage and type
                if (StringUtils.isBlank(spValue)) {
                    spatialType = CoverageType.UNKNOWN.type();
                    spatialValue = SpatialValue.UNKNOWN.value();

                } else {
                    spatialType = CoverageType.KML.type();
                    spatialValue = spValue;
                }
            }
            Location location = this.dmService.getLocationByCoverageType(spatialType, spatialValue);
            if (location == null) {
                location = new Location();
                location.setSpatialType(spatialType);
                location.setSpatialCoverage(spatialValue);
                this.dmService.saveLocation(location);
            }
            //save the location inot collection
            collection.setLocation(location);

            // setup a default permissions.
//            List<Permission> defaultPermissions = setDefaultPermissions();
//            collection.setPermissions(defaultPermissions);

            List<CPermission> coDefaultPerms = setCollectionDefaultPermissions(collection);
            collection.setCpermissions(coDefaultPerms);


            this.dmService.createCollection(collection, dataStorePath);
            // set view type is user
            viewType = ActConstants.UserViewType.USER.viewType();

            // record down the event
            recordAuditEvent();

            // convert any newline in the description into a br html tag
            String textAreaDesc = collection.getDescription();
            String htmlDesc = nlToBr(textAreaDesc);
            collection.setDescription(htmlDesc);

            // populate the rifcs registration if enabled
            String mdRegEnabledStr = configSetting.getPropValue(ConfigSettings.ANDS_RIFCS_REG_ENABLED);
            mdRegEnabled = Boolean.valueOf(mdRegEnabledStr).booleanValue();

            //set the full permissions for owner
            setupFullPermissions();
            //if metadata registration disabled. then we remove the metadata registration permission
            if (!mdRegEnabled) {
                permissionBean.setMdRegAllowed(false);
            }

            // populate the collection links
            populateLinksInUsrCollection();
            // set action successful message
            setActionSuccessMsg(getText("create.collection.success"));
            // set page title and navigation label
            setNavAfterSuccess();
        } catch (Exception e) {
            logger.error(e.getMessage());
            addActionError(getText("failed.to.create.collection"));
            return INPUT;
        }

        return SUCCESS;
    }

    public void validateCreateCollection() {

        if (StringUtils.isBlank(collection.getName())) {
            addFieldError("collection.name", getText("collection.name.required"));
        }

        Date fromDate = collection.getDateFrom();
        Date toDate = collection.getDateTo();

        if ((fromDate != null && toDate == null) || (fromDate == null && toDate != null)) {
            addFieldError("fromToDate", getText("collection.fromDate.and.toDate.must.be.provided"));
        }

        if (fromDate != null && toDate != null) {
            if (fromDate.compareTo(toDate) > 0) {
                addFieldError("invalidFromToDate", getText("collection.start.date.must.be.earlier.than.to.datetime"));
            }
        }

        if (StringUtils.isBlank(collection.getDescription())) {
            addFieldError("collection.description", getText("collection.description.required"));
        }

        if (StringUtils.isNotBlank(collection.getName())) {
            if (!CaptureUtil.notGTFixedLength(collection.getName(), 80)) {
                addFieldError("collection.name.length", getText("collection.name.max.length"));
            }
        }

        if (StringUtils.isNotBlank(collection.getDescription())) {
            if (!CaptureUtil.notGTFixedLength(collection.getDescription(), 4000)) {
                addFieldError("collection.desc.length", getText("collection.desc.max.length"));
            }
        }

        if (StringUtils.isNotBlank(collection.getSpatialCoverage())) {
            if (!CaptureUtil.notGTFixedLength(collection.getSpatialCoverage(), 255)) {
                addFieldError("collection.coverage.length", getText("collection.coverage.max.length"));
            }
        }

    }

    private List<CPermission> setCollectionDefaultPermissions(Collection co) {
        List<CPermission> defaultPerms = new ArrayList<CPermission>();
        //all registered user group permission
        CPermission allRegUserPerm = new CPermission();
        allRegUserPerm.setPermType(PermType.ALLREGUSER.code());
        User allRegUser = this.userService.getVirtualUser(UserType.ALLREGUSER.code());
        allRegUserPerm.setCollection(co);
        allRegUserPerm.setPermForUser(allRegUser);
        CPermission anonymousPerm = new CPermission();
        anonymousPerm.setPermType(PermType.ANONYMOUS.code());
        User anonymous = this.userService.getVirtualUser(UserType.ANONYMOUS.code());
        anonymousPerm.setCollection(co);
        anonymousPerm.setPermForUser(anonymous);
        defaultPerms.add(allRegUserPerm);
        defaultPerms.add(anonymousPerm);
        return defaultPerms;
    }

    private List<Permission> setDefaultPermissions() {
        // all-registered user
        Permission allUserPerm = new Permission();
        // set the permission type;
        allUserPerm.setPermType(PermType.ALLREGUSER.code());

        if (allRegUser == null) {
            allRegUser = this.userService.getVirtualUser(UserType.ALLREGUSER.code());
        }
        allUserPerm.setCollection(collection);
        allUserPerm.setPermissionForUser(allRegUser);

        // anonymous user
        Permission anonyPerm = new Permission();
        // set the permission type.
        anonyPerm.setPermType(PermType.ANONYMOUS.code());

        if (anonymous == null) {
            anonymous = this.userService.getVirtualUser(UserType.ANONYMOUS.code());
        }
        anonyPerm.setCollection(collection);
        anonyPerm.setPermissionForUser(anonymous);

        List<Permission> defaultPerms = new ArrayList<Permission>();
        defaultPerms.add(allUserPerm);
        defaultPerms.add(anonyPerm);
        return defaultPerms;
    }

    private void recordAuditEvent() {
        AuditEvent ev = new AuditEvent();
        ev.setCreatedTime(GregorianCalendar.getInstance().getTime());
        ev.setEvent(collection.getName() + " has been created");
        ev.setEventOwner(collection.getOwner());
        ev.setOperator(user);
        recordActionAuditEvent(ev);
    }

    // set the page title and navigation label
    private void setNavAfterSuccess() {
        // set the new page title after successful creating a new collection.
        String startNav = getText("mycollection.nav.label.name");
        String secondNav = collection.getName();
        String startNavLink = ActConstants.USER_LIST_COLLECTION_ACTION;

        String secondNavLink = ActConstants.VIEW_COLLECTION_DETAILS_ACTION + "?collection.id=" + collection.getId() + "&collection.owner.id="
                + collection.getOwner().getId() + "&viewType=" + viewType;
        setPageTitle(startNav, secondNav);
        navigationBar = generateNavLabel(startNav, startNavLink, secondNav, secondNavLink, null, null);
    }

    // check the dataset path
    private boolean checkDataStorePath() {
        String dataStorePath = configSetting.getPropValue(ConfigSettings.DATA_STORE_LOCATION);
        if (StringUtils.isBlank(dataStorePath)) {
            addActionError(getText("datastore.path.undefined.error"));
            return false;
        }
        try {
            if (!this.dmService.checkWritePermission(dataStorePath)) {
                addActionError(getText("datastore.path.permission.error"));
                return false;
            }
        } catch (Exception e) {
            logger.error(e.getMessage());
            addActionError(getText("datastore.path.check.permission.failed"));
            return false;
        }
        return true;
    }

    public boolean isMdRegEnabled() {
        return mdRegEnabled;
    }

    public void setMdRegEnabled(boolean mdRegEnabled) {
        this.mdRegEnabled = mdRegEnabled;
    }

    public boolean isGlobalCoverage() {
        return globalCoverage;
    }

    public void setGlobalCoverage(boolean globalCoverage) {
        this.globalCoverage = globalCoverage;
    }
}
