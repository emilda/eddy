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
import au.edu.monash.merc.capture.dto.PartyBean;
import au.edu.monash.merc.capture.dto.ProjectBean;
import au.edu.monash.merc.capture.dto.PublishBean;
import au.edu.monash.merc.capture.exception.DataCaptureException;
import au.edu.monash.merc.capture.rifcs.PartyActivityWSService;
import au.edu.monash.merc.capture.service.ldap.LdapService;
import au.edu.monash.merc.capture.util.CaptureUtil;
import au.edu.monash.merc.capture.util.ldap.LdapUser;
import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Controller;

import java.util.ArrayList;
import java.util.GregorianCalendar;
import java.util.List;

@Scope("prototype")
@Controller("data.mdRegAction")
public class MDRegisterAction extends DMCoreAction {

    @Autowired
    private PartyActivityWSService paWsService;

    @Autowired
    private LdapService ldapService;

    private String nlaId;

    private List<PartyBean> partyList;

    private List<ProjectBean> projectList;

    private Rights rights;

    private String accessRights;

    private String anzSrcCode;

    private String physicalAddress;

    private PartyBean addedPartyBean;

    private String searchCnOrEmail;

    private List<PartyBean> foundPartyBeans;

    private Logger logger = Logger.getLogger(this.getClass().getName());

    public String showMdReg() {
        setViewColDetailLink(ActConstants.VIEW_COLLECTION_DETAILS_ACTION);
        try {
            user = retrieveLoggedInUser();
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.get.user.failed"));
            setNavAfterExc();
            return ERROR;
        }

        try {
            collection = this.dmService.getCollection(collection.getId(), collection.getOwner().getId());
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.get.collection.failed"));
            setNavAfterExc();
            return ERROR;
        }

        //check if none ldap user supported for md registration or not.
        String noneLdapSupported = configSetting.getPropValue(ConfigSettings.ANDS_MD_REGISTER_FOR_NON_LDAP_USER_SUPPORTED);
        boolean noneLdapSupprotForMd = Boolean.valueOf(noneLdapSupported);
        //see if it's a ldap user
        String passwd = user.getPassword();
        boolean monUser = true;
        if (!StringUtils.endsWithIgnoreCase(passwd, "ldap")) {
            monUser = false;
        }

        if (!monUser && !noneLdapSupprotForMd) {
            addActionError(getText("ands.md.registration.none.ldap.user.not.supported"));
            setNavAfterExc();
            return ERROR;
        }

        //only the owner and system admin can publish this collection
        if ((user.getId() != collection.getOwner().getId()) && (user.getUserType() != UserType.ADMIN.code() && (user.getUserType() != UserType.SUPERADMIN.code()))) {
            logger.error("The user is neither the owner of this collection nor the administrator, unable to register metadata for this collection.");
            addActionError(getText("ands.md.registration.permission.denied"));
            setNavAfterExc();
            return ERROR;
        }

        // check the existed parties if any
        List<Party> ps = new ArrayList<Party>();
        try {
            ps = this.dmService.getPartiesByCollectionId(collection.getId());
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.check.existed.parties.failed"));
            setNavAfterExc();
            return ERROR;
        }

        // check the existed activities if any
        List<Activity> as = new ArrayList<Activity>();
        try {
            as = this.dmService.getActivitiesByCollectionId(collection.getId());
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.check.existed.activities.failed"));
            setNavAfterExc();
            return ERROR;
        }

        // check the existed rights
        try {
            Rights existedRights = this.dmService.getRightsByCollectionId(collection.getId());
            if (existedRights != null) {
                rights = existedRights;
            } else {
                //just create an empty rights
                rights = new Rights();
            }
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.check.license.failed"));
            setNavAfterExc();
            return ERROR;
        }

        //generate the access rights
        try {
            Permission perm = this.dmService.getAnonymousPerm(collection.getId());
            if (perm.isViewAllowed()) {
                accessRights = getText("collection.access.type.public");
            } else {
                User owner = collection.getOwner();
                accessRights = getText("collection.access.type.private", new String[]{owner.getDisplayName(), owner.getEmail()});
            }
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.check.access.rights.failed"));
            setNavAfterExc();
            return ERROR;
        }

        PartyBean partyBean = null;
        List<ProjectBean> prolist = null;
        if (monUser) {
            // get researcher nla id from rm ws
            try {
                nlaId = paWsService.getNlaId(user.getUniqueId());
            } catch (Exception e) {
                String errorMsg = e.getMessage();
                logger.error(getText("ands.md.registration.ws.failed") + ", " + e);
                boolean keepdoing = false;
                if (StringUtils.containsIgnoreCase(errorMsg, "NLA Id not found") || StringUtils.containsIgnoreCase(errorMsg, "Invalid authcate username")) {
                    keepdoing = true;
                }
                if (!keepdoing) {
                    setForRMWSException(errorMsg);
                    return ERROR;
                }
            }
            // get the researcher party from rm ws

            if (nlaId != null) {
                try {
                    partyBean = paWsService.getParty(nlaId);
                    // set the paty as selected if party available
                    if (partyBean != null) {
                        partyBean.setSelected(true);
                    }
                } catch (Exception e) {
                    String errorMsg = e.getMessage();
                    logger.error(getText("ands.md.registration.ws.failed") + ", " + e);
                    boolean keepdoing = false;

                    if (StringUtils.containsIgnoreCase(errorMsg, "Invalid party id")) {
                        keepdoing = true;
                    }
                    if (!keepdoing) {
                        setForRMWSException(errorMsg);
                        return ERROR;
                    }
                }
            }

            // get the project summary from rm ws
            if (nlaId != null) {
                try {
                    // get activity summary
                    prolist = paWsService.getProjects(nlaId);
                } catch (Exception e) {
                    String errorMsg = e.getMessage();
                    logger.error(getText("ands.md.registration.ws.failed") + ", " + e);
                    boolean keepdoing = false;

                    if (StringUtils.containsIgnoreCase(errorMsg, "Projects not found") || StringUtils.containsIgnoreCase(errorMsg, "Invalid NLA Id")) {
                        keepdoing = true;
                    }

                    if (!keepdoing) {
                        setForRMWSException(errorMsg);
                        return ERROR;
                    }
                }
            }
        }
        // merge previous existed parties if any
        populateAllParties(ps, partyBean);
        // merge previous existed project summary
        populateAllActivities(as, prolist);
        setNavAfterSuccess();
        return SUCCESS;
    }

    private void setForRMWSException(String errorMsg) {
        addActionError(getText("ands.md.registration.ws.failed") + ", " + errorMsg);
        setNavAfterExc();
    }

    private void populateAllParties(List<Party> existedParties, PartyBean rmpb) {
        if (partyList == null) {
            partyList = new ArrayList<PartyBean>();
            // add the rm party
            if (rmpb != null) {
                partyList.add(rmpb);
            }
        }
        if (existedParties != null && existedParties.size() > 0) {
            for (Party party : existedParties) {
                String partykey = party.getPartyKey();
                // create a previous PartyBean
                PartyBean existedParty = copyPartyToPartyBean(party);
                existedParty.setSelected(true);
                // if rmpb is not null, then we compare it with exsited parties which previous populated
                // if key is not the same, then we add it into the list,
                // if rmpb is null, then we add all existed parties
                if (rmpb != null) {
                    String rmPbKey = rmpb.getPartyKey();
                    if (!rmPbKey.equals(partykey)) {
                        partyList.add(existedParty);
                    }
                } else {
                    partyList.add(existedParty);
                }
            }
        }
    }

    private void populateAllActivities(List<Activity> existedActivities, List<ProjectBean> rmProjList) {
        if (projectList == null) {
            projectList = new ArrayList<ProjectBean>();
        }
        // sign the rm project summary list to project list
        if (rmProjList != null) {
            projectList = rmProjList;
        }

        if (projectList != null && projectList.size() > 0) {
            for (ProjectBean projb : projectList) {
                if (existedActivities != null && existedActivities.size() > 0) {
                    for (Activity a : existedActivities) {
                        if (projb.getActivityKey().equals(a.getActivityKey())) {
                            projb.setSelected(true);
                        }
                    }
                }
            }
        }
    }


    public String preRegMd() {
        setViewColDetailLink(ActConstants.VIEW_COLLECTION_DETAILS_ACTION);
        List<PartyBean> selectedPas = new ArrayList<PartyBean>();
        for (PartyBean partyb : partyList) {
            if (partyb.isSelected()) {
                selectedPas.add(partyb);
            }
        }
        partyList = selectedPas;

        List<ProjectBean> selectedActs = new ArrayList<ProjectBean>();
        if (projectList != null) {
            for (ProjectBean projb : projectList) {
                if (projb.isSelected()) {
                    selectedActs.add(projb);
                }
            }
            projectList = selectedActs;
        }

        anzSrcCode = configSetting.getPropValue(ConfigSettings.ANDS_RIFCS_REG_ANZSRC_CODE);
        physicalAddress = configSetting.getPropValue(ConfigSettings.DATA_COLLECTIONS_PHYSICAL_LOCATION);
        setNavAfterSuccess();
        return SUCCESS;
    }

    public void validatePreRegMd() {
        boolean hasError = false;
        boolean atLeastOnePartySelected = false;
        if (partyList != null) {
            for (PartyBean ptb : partyList) {
                if (ptb.isSelected()) {
                    atLeastOnePartySelected = true;
                }
            }
        }
        if (!atLeastOnePartySelected) {
            addFieldError("partyid", getText("ands.md.registration.party.required"));
            hasError = true;
        }
        if (StringUtils.isBlank(rights.getRightsType())) {
            addFieldError("rights", getText("ands.md.registration.license.required"));
            hasError = true;
        }
        // set navigations
        if (hasError) {
            setNavAfterExc();
            setViewColDetailLink(ActConstants.VIEW_COLLECTION_DETAILS_ACTION);
        }
    }

    public String mdReg() {
        setViewColDetailLink(ActConstants.VIEW_COLLECTION_DETAILS_ACTION);
        try {
            user = retrieveLoggedInUser();
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.get.user.failed"));
            setNavAfterExc();
            return ERROR;
        }

        //check if none ldap user supported for md registration or not.
        String noneLdapSupported = configSetting.getPropValue(ConfigSettings.ANDS_MD_REGISTER_FOR_NON_LDAP_USER_SUPPORTED);
        boolean noneLdapSupprotForMd = Boolean.valueOf(noneLdapSupported);

        String passwd = user.getPassword();
        if (!StringUtils.equals(passwd, "ldap") && !noneLdapSupprotForMd) {
            addActionError(getText("ands.md.registration.none.ldap.user.not.supported"));
            setNavAfterExc();
            return ERROR;
        }

        if ((user.getId() != collection.getOwner().getId()) && (user.getUserType() != UserType.ADMIN.code() && (user.getUserType() != UserType.SUPERADMIN.code()))) {
            logger.error("The user is neither the owner of this collection nor the administrator, unable to register metadata for this collection.");
            addActionError(getText("ands.md.registration.permission.denied"));
            setNavAfterExc();
            return ERROR;
        }

        try {
            collection = this.dmService.getCollection(collection.getId(), collection.getOwner().getId());
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.get.collection.failed"));
            setNavAfterExc();
            return ERROR;
        }

        //check the unique key for this collection
        String existedUniqueKey = collection.getUniqueKey();
        if (StringUtils.isBlank(existedUniqueKey)) {
            try {
                String uuidKey = pidService.genUUIDWithPrefix();
                collection.setUniqueKey(uuidKey);
            } catch (Exception e) {
                logger.error(e);
                addActionError(getText("ands.md.registration.create.unique.key.failed"));
                setNavAfterExc();
                return ERROR;
            }
        }

        // populate the url of this collection
        String serverQName = getServerQName();
        String appContext = getAppContextPath();
        StringBuffer collectionUrl = new StringBuffer();
        collectionUrl.append(serverQName).append(appContext).append(ActConstants.URL_PATH_DEIM);
        collectionUrl.append("pub/viewColDetails.jspx?collection.id=" + collection.getId() + "&collection.owner.id=" + collection.getOwner().getId()
                + "&viewType=anonymous");
        // create handle if handle service is enabled
        String hdlEnabledStr = configSetting.getPropValue(ConfigSettings.HANDLE_SERVICE_ENABLED);
        String existedHandle = collection.getPersistIdentifier();
        // if no existed hanlde. it will be created if handle ws is enabaled
        if (existedHandle == null) {
            if (Boolean.valueOf(hdlEnabledStr)) {
                try {
                    String handle = pidService.genHandleIdentifier(collectionUrl.toString());
                    // String hdlResolver = configSetting.getPropValue(ConfigSettings.HANDLE_RESOLVER_SERVER);
                    // collection.setPersistIdentifier(hdlResolver + "/" + handle);
                    collection.setPersistIdentifier(handle);
                } catch (Exception e) {
                    logger.error(e);
                    addActionError(getText("ands.md.registration.create.handle.failed"));
                    setNavAfterExc();
                    return ERROR;
                }
            } else {
                collection.setPersistIdentifier(collection.getUniqueKey());
            }
        }

        // set the collection as published
        collection.setPublished(true);

        // populate the publish bean
        PublishBean pubBean = new PublishBean();
        pubBean.setPartyList(partyList);
        pubBean.setActivityList(projectList);
        pubBean.setCollection(collection);
        pubBean.setRights(rights);
        pubBean.setAccessRights(accessRights);

        // get the rifcs files store location
        String rifcsStoreLocation = configSetting.getPropValue(ConfigSettings.ANDS_RIFCS_STORE_LOCATION);
        pubBean.setRifcsStoreLocation(rifcsStoreLocation);
        String anzsrcCode = configSetting.getPropValue(ConfigSettings.ANDS_RIFCS_REG_ANZSRC_CODE);
        pubBean.setAnzsrcCode(anzsrcCode);
        String address = configSetting.getPropValue(ConfigSettings.DATA_COLLECTIONS_PHYSICAL_LOCATION);
        pubBean.setPhysicalAddress(address);
        pubBean.setRifcsGroupName(configSetting.getPropValue(ConfigSettings.ANDS_RIFCS_REG_GROUP_NAME));
        // set the url - electronic url
        pubBean.setElectronicURL(CaptureUtil.replaceURLAmpsands(collectionUrl.toString()));
        pubBean.setAppName(getServerQName());
        try {
            this.dmService.savePublishInfo(pubBean);
            // save the metadata registration auditing info
            recordMDRegAuditEvent();
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("ands.md.registration.register.failed"));
            setNavAfterExc();
            return ERROR;
        }
        addActionMessage(getText("ands.md.registration.register.success"));
        setNavAfterSuccess();
        return SUCCESS;
    }

    // save the auditing information for metadata registration
    private void recordMDRegAuditEvent() {
        AuditEvent ev = new AuditEvent();
        ev.setCreatedTime(GregorianCalendar.getInstance().getTime());
        ev.setEvent(getText("ands.md.registration.audit.info", new String[]{collection.getName()}));
        ev.setEventOwner(collection.getOwner());
        ev.setOperator(user);
        recordActionAuditEvent(ev);
    }

    public String showSearchParty() {

        return SUCCESS;
    }


    public String searchParty() {
        if (StringUtils.isBlank(searchCnOrEmail)) {
            addFieldError("cnoremail", getText("ands.md.registration.search.party.cnoremail.must.be.provided"));
            return INPUT;
        }
        try {
            foundPartyBeans = searchPartyFromDb(searchCnOrEmail);
        } catch (Exception ex) {
            logger.error(ex.getMessage());
            addActionError(getText("ands.md.registration.search.party.failed"));
            return ERROR;
        }
        if (foundPartyBeans != null && foundPartyBeans.size() > 0) {
            return SUCCESS;
        }

        if (foundPartyBeans == null) {
            foundPartyBeans = new ArrayList<PartyBean>();
        }
        try {
            PartyBean pb = searchPartyFromRMWS(searchCnOrEmail);
            if (pb != null) {
                foundPartyBeans.add(pb);
            }
        } catch (Exception ex) {
            logger.error(ex.getMessage());
            addActionError(getText("ands.md.registration.ws.failed") + ", Failed to find a researcher");
            return ERROR;
        }
        //if party not found
        if (foundPartyBeans.size() == 0) {
            setActionSuccessMsg(getText("ands.md.registration.search.party.not.found"));
            setSearchValueToPartyBean(searchCnOrEmail);
            return PNOTFOUND;
        }
        return SUCCESS;
    }

    private List<PartyBean> searchPartyFromDb(String userNameOrEmail) {
        List<PartyBean> tempPbs = new ArrayList<PartyBean>();
        List<Party> foundParties = this.dmService.getPartyByUserNameOrEmail(searchCnOrEmail);
        if (foundParties != null && foundParties.size() > 0) {
            for (Party p : foundParties) {
                PartyBean partyBean = copyPartyToPartyBean(p);
                tempPbs.add(partyBean);
            }
        }
        return tempPbs;
    }

    private PartyBean searchPartyFromRMWS(String userNameOrEmail) {

        LdapUser ldapUser = null;
        try {
            ldapUser = ldapService.searchLdapUser(searchCnOrEmail);
        } catch (Exception e) {
            throw new DataCaptureException(e);
        }

        if (ldapUser == null) {
            logger.error("can't find an researcher from ldap");
            return null;
        }
        //if found the LDAP user, then search the rm web service for the party
        try {
            String rmNlaId = paWsService.getNlaId(ldapUser.getUid());
            // get party
            PartyBean rmPartyBean = paWsService.getParty(rmNlaId);
            return rmPartyBean;
        } catch (Exception e) {
            String errorMsg = e.getMessage();
            if (StringUtils.containsIgnoreCase(errorMsg, "NLA Id not found") || StringUtils.containsIgnoreCase(errorMsg, "Invalid authcate username")) {
                logger.error(errorMsg);
                return null;
            } else {
                throw new DataCaptureException(e);
            }
        }
    }

    public String selectParty() {
        if (selectedPartyHasErrors()) {
            return INPUT;
        }
        for (PartyBean pb : foundPartyBeans) {
            if (pb.isSelected()) {
                addedPartyBean = pb;
            }
        }
        return SUCCESS;
    }

    private boolean selectedPartyHasErrors() {
        int totalSelectedCounter = 0;
        for (PartyBean pb : foundPartyBeans) {
            if (pb.isSelected()) {
                totalSelectedCounter++;
            }
        }
        if (totalSelectedCounter == 0) {
            addFieldError("nopartyselected", getText("ands.md.registration.add.party.one.party.must.be.selected"));
            return true;
        }
        if (totalSelectedCounter > 1) {
            addFieldError("morepartyselected", getText("ands.md.registration.add.party.only.one.party.needed"));
            return true;
        }
        return false;
    }

    private PartyBean copyPartyToPartyBean(Party p) {
        PartyBean pb = new PartyBean();
        pb.setId(p.getId());
        pb.setPartyKey(p.getPartyKey());
        pb.setPersonTitle(p.getPersonTitle());
        pb.setPersonGivenName(p.getPersonGivenName());
        pb.setPersonFamilyName(p.getPersonFamilyName());
        pb.setUrl(p.getUrl());
        pb.setEmail(p.getEmail());
        pb.setAddress(p.getAddress());
        pb.setIdentifierType(p.getIdentifierType());
        pb.setIdentifierValue(p.getIdentifierValue());
        pb.setOriginateSourceType(p.getOriginateSourceType());
        pb.setOriginateSourceValue(p.getOriginateSourceValue());
        pb.setGroupName(p.getGroupName());
        pb.setFromRm(p.isFromRm());
        return pb;
    }

    private Party copyPartyBeanToParty(PartyBean pb) {
        Party pa = new Party();
        if (pb.getId() != 0) {
            pa.setId(pb.getId());
        }
        pa.setPartyKey(pb.getPartyKey());
        pa.setPersonTitle(pb.getPersonTitle());
        pa.setPersonGivenName(pb.getPersonGivenName());
        pa.setPersonFamilyName(pb.getPersonFamilyName());
        pa.setUrl(pb.getUrl());
        pa.setEmail(pb.getEmail());
        pa.setAddress(pb.getAddress());
        pa.setIdentifierType(pb.getIdentifierType());
        pa.setIdentifierValue(pb.getIdentifierValue());
        pa.setOriginateSourceType(pb.getOriginateSourceType());
        pa.setOriginateSourceValue(pb.getOriginateSourceValue());
        pa.setGroupName(pb.getGroupName());
        pa.setFromRm(pb.isFromRm());
        return pa;
    }

    private void setSearchValueToPartyBean(String searchValue) {
        addedPartyBean = new PartyBean();
        addedPartyBean.setGroupName(configSetting.getPropValue(ConfigSettings.ANDS_RIFCS_REG_GROUP_NAME));
        if (StringUtils.isNotBlank(searchCnOrEmail)) {
            if (StringUtils.contains(searchCnOrEmail, "@")) {
                addedPartyBean.setEmail(searchCnOrEmail);
            } else {
                String[] names = StringUtils.split(searchCnOrEmail, " ");
                if (names != null && names.length >= 2) {
                    String firstName = names[0];
                    String lastName = names[1];
                    addedPartyBean.setPersonGivenName(firstName);
                    addedPartyBean.setPersonFamilyName(lastName);
                }
                if (names != null && names.length == 1) {
                    String firstName = names[0];
                    addedPartyBean.setPersonGivenName(firstName);
                }
            }
        }
    }

    public String showAddUDParty() {
        return SUCCESS;
    }

    public String addUDParty() {

        if (addedPartyBean != null) {
            try {
                Party p = dmService.getPartyByEmail(addedPartyBean.getEmail());
                if (p != null) {
                    logger.error(getText("ands.md.registration.add.party.already.existed"));
                    addActionError(getText("ands.md.registration.add.party.already.existed"));
                    return INPUT;
                }
            } catch (Exception ex) {
                logger.error("failed to get a party, " + ex.getMessage());
                addActionError(getText("ands.md.registration.add.party.failed"));
                return INPUT;
            }

            try {
                PartyBean partyBean = searchPartyFromRMWS(addedPartyBean.getEmail());
                if (partyBean != null) {
                    logger.error(getText("ands.md.registration.add.party.already.existed"));
                    addActionError(getText("ands.md.registration.add.party.already.existed"));
                    return INPUT;
                }
            } catch (Exception ex) {
                logger.error("failed to search a party from research master web service, " + ex.getMessage());
                addActionError(getText("ands.md.registration.add.party.failed"));
                return INPUT;
            }
        }
        try {
            //create a new party
            Party p = new Party();
            p = copyPartyBeanToParty(addedPartyBean);
            String localKey = pidService.genUUIDWithPrefix();
            p.setPartyKey(localKey);
            p.setIdentifierValue(localKey);
            p.setIdentifierType("local");
            p.setOriginateSourceType("authoritative");
            this.dmService.saveParty(p);
            addedPartyBean = copyPartyToPartyBean(p);
        } catch (Exception e) {
            logger.error("failed to save party, " + e.getMessage());
            addActionError(getText("ands.md.registration.add.party.failed"));
            return INPUT;
        }
        // just return
        return SUCCESS;
    }

    public String showEditUDParty() {
        try {
            Party p = dmService.getPartyByPartyKey(addedPartyBean.getPartyKey());
            if (p != null) {
                addedPartyBean = copyPartyToPartyBean(p);
            } else {
                addActionError(getText("ands.md.registration.edit.party.not.existed"));
                return ERROR;
            }
        } catch (Exception ex) {
            addActionError(getText("ands.md.registration.edit.party.get.party.failed"));
            return ERROR;
        }
        return SUCCESS;
    }

    public String updateUDParty() {
        try {
            if (StringUtils.isBlank(addedPartyBean.getPartyKey())) {
                addFieldError("partyKey", getText("ands.md.registration.edit.party.key.must.be.provided"));
                return INPUT;
            }
            Party party = copyPartyBeanToParty(addedPartyBean);
            this.dmService.updateParty(party);
        } catch (Exception ex) {
            addActionError(getText("ands.md.registration.edit.party.failed"));
            return ERROR;
        }
        return SUCCESS;
    }


    private void setNavAfterSuccess() {

        String startNav = null;
        String startNavLink = null;

        String secondNav = collection.getName();
        String secondNavLink = null;
        String thirdNav = getText("ands.md.registration.title");
        if (viewType != null) {
            if (viewType.equals(ActConstants.UserViewType.USER.toString())) {
                startNav = getText("mycollection.nav.label.name");
                startNavLink = ActConstants.USER_LIST_COLLECTION_ACTION;
                secondNavLink = ActConstants.VIEW_COLLECTION_DETAILS_ACTION + "?collection.id=" + collection.getId() + "&collection.owner.id="
                        + collection.getOwner().getId() + "&viewType=" + viewType;
            }
            if (viewType.equals(ActConstants.UserViewType.ALL.toString())) {
                startNav = getText("allcollection.nav.label.name");
                startNavLink = ActConstants.LIST_ALL_COLLECTIONS_ACTION;
                secondNavLink = ActConstants.VIEW_COLLECTION_DETAILS_ACTION + "?collection.id=" + collection.getId() + "&amp;collection.owner.id="
                        + collection.getOwner().getId() + "&amp;viewType=" + viewType;
            }
            // set the new page title after successful creating a new collection.
            setPageTitle(startNav, secondNav + " - " + thirdNav);
            navigationBar = generateNavLabel(startNav, startNavLink, secondNav, secondNavLink, thirdNav, null);
        }
    }

    private void setNavAfterExc() {

        String startNav = null;
        String startNavLink = null;

        String secondNav = collection.getName();
        String secondNavLink = null;
        String thirdNav = getText("ands.md.registration.title");
        if (viewType != null) {
            if (viewType.equals(ActConstants.UserViewType.USER.toString())) {
                startNav = getText("mycollection.nav.label.name");
                startNavLink = ActConstants.USER_LIST_COLLECTION_ACTION;
                secondNavLink = ActConstants.VIEW_COLLECTION_DETAILS_ACTION + "?collection.id=" + collection.getId() + "&collection.owner.id="
                        + collection.getOwner().getId() + "&viewType=" + viewType;
            }
            if (viewType.equals(ActConstants.UserViewType.ALL.toString())) {
                startNav = getText("allcollection.nav.label.name");
                startNavLink = ActConstants.LIST_ALL_COLLECTIONS_ACTION;
                secondNavLink = ActConstants.VIEW_COLLECTION_DETAILS_ACTION + "?collection.id=" + collection.getId() + "&collection.owner.id="
                        + collection.getOwner().getId() + "&viewType=" + viewType;
            }
            // set the new page title after successful creating a new collection.
            setPageTitle(startNav, secondNav + " - " + thirdNav + " Error");
            navigationBar = generateNavLabel(startNav, startNavLink, secondNav, secondNavLink, thirdNav, null);
        }
    }

    public void setPaWsService(PartyActivityWSService paWsService) {
        this.paWsService = paWsService;
    }

    public void setLdapService(LdapService ldapService) {
        this.ldapService = ldapService;
    }

    public String getNlaId() {
        return nlaId;
    }

    public void setNlaId(String nlaId) {
        this.nlaId = nlaId;
    }

    public List<ProjectBean> getProjectList() {
        return projectList;
    }

    public void setProjectList(List<ProjectBean> projectList) {
        this.projectList = projectList;
    }

    public Rights getRights() {
        return rights;
    }

    public void setRights(Rights rights) {
        this.rights = rights;
    }

    public String getAccessRights() {
        return accessRights;
    }

    public void setAccessRights(String accessRights) {
        this.accessRights = accessRights;
    }

    public List<PartyBean> getPartyList() {
        return partyList;
    }

    public void setPartyList(List<PartyBean> partyList) {
        this.partyList = partyList;
    }

    public String getAnzSrcCode() {
        return anzSrcCode;
    }

    public void setAnzSrcCode(String anzSrcCode) {
        this.anzSrcCode = anzSrcCode;
    }

    public String getPhysicalAddress() {
        return physicalAddress;
    }

    public void setPhysicalAddress(String physicalAddress) {
        this.physicalAddress = physicalAddress;
    }

    public PartyBean getAddedPartyBean() {
        return addedPartyBean;
    }

    public void setAddedPartyBean(PartyBean addedPartyBean) {
        this.addedPartyBean = addedPartyBean;
    }

    public String getSearchCnOrEmail() {
        return searchCnOrEmail;
    }

    public void setSearchCnOrEmail(String searchCnOrEmail) {
        this.searchCnOrEmail = searchCnOrEmail;
    }

    public List<PartyBean> getFoundPartyBeans() {
        return foundPartyBeans;
    }

    public void setFoundPartyBeans(List<PartyBean> foundPartyBeans) {
        this.foundPartyBeans = foundPartyBeans;
    }
}
