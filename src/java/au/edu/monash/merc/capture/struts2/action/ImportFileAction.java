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
import au.edu.monash.merc.capture.domain.AuditEvent;
import au.edu.monash.merc.capture.domain.Dataset;
import au.edu.monash.merc.capture.domain.RestrictAccess;
import au.edu.monash.merc.capture.dto.FileImportResponse;
import au.edu.monash.merc.capture.util.CaptureUtil;
import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Controller;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.Date;
import java.util.GregorianCalendar;
import java.util.HashMap;
import java.util.Map;

@Scope("prototype")
@Controller("data.importFileAction")
public class ImportFileAction extends DMCoreAction {

    private FileImportResponse importResponse;

    private boolean extractable;

    private File upload;

    private String uploadContentType;

    private String uploadFileName;

    private boolean raEnabled;

    private Logger logger = Logger.getLogger(this.getClass().getName());

    public String importFile() {
        importResponse = new FileImportResponse();
        // check the collection and user
        try {
            user = retrieveLoggedInUser();
            collection = this.dmService.getCollection(collection.getId(), collection.getOwner().getId());
            collection.setModifiedTime(GregorianCalendar.getInstance().getTime());
            collection.setModifiedByUser(user);
        } catch (Exception e) {
            logger.error(e);
            importResponse.setSucceed(false);
            importResponse.setMessage(getText("dataset.import.get.collection.details.failed"));
            return SUCCESS;
        }

        // check the permissions
        try {
            permissionBean = checkPermission(collection.getId(), collection.getOwner().getId());
        } catch (Exception e) {
            logger.error(e);
            importResponse.setSucceed(false);
            importResponse.setMessage(getText("check.permissions.error"));
            return SUCCESS;
        }

        if (!permissionBean.isImportAllowed()) {
            logger.error(getText("dataset.import.permission.denied"));
            importResponse.setSucceed(false);
            importResponse.setMessage(getText("dataset.import.permission.denied"));
            return SUCCESS;
        }

        // check the file exists or not
        try {
            if (this.dmService.checkDatasetNameExisted(uploadFileName, collection.getId())) {
                importResponse.setSucceed(false);
                importResponse.setMessage(getText("dataset.import.file.already.existed", new String[]{uploadFileName}));
                logger.error(getText("dataset.import.file.already.existed", new String[]{uploadFileName}));
                return SUCCESS;
            }
        } catch (Exception e) {
            logger.error(e);
            importResponse.setSucceed(false);
            importResponse.setMessage(getText("dataset.import.check.file.name.error"));
            return SUCCESS;
        }

        //restricted access
        if (raEnabled) {
            Date raEndDate = restrictAccess.getEndDate();
            if (raEndDate == null) {
                importResponse.setSucceed(false);
                importResponse.setMessage(getText("restrict.access.end.date.must.be.provided"));
                return SUCCESS;
            }
            Date today = CaptureUtil.getToday();

            //set the restricted access day as today
            restrictAccess.setStartDate(today);

            //if the end date is before today
            if (isEndDateExpired(raEndDate)) {
                importResponse.setSucceed(false);
                importResponse.setMessage(getText("restrict.access.end.input.end.date.expired"));
                return SUCCESS;
            }

            //if the end date is less min 30 days from today
            if (isBeforeMinRaEndDate(today, raEndDate)) {
                importResponse.setSucceed(false);
                importResponse.setMessage(getText("restrict.access.end.date.is.before.min.end.date"));
                return SUCCESS;
            }

            //if the end date is more than 18 months away from today
            if (isAfterMaxRaEndDate(today, raEndDate)) {
                importResponse.setSucceed(false);
                importResponse.setMessage(getText("restrict.access.end.date.is.after.max.end.date"));
                return SUCCESS;
            }
        }

        // start to upload the file
        FileInputStream fis = null;
        try {
            // read the uploading inputstream
            // fis = new FileInputStream(upload);
            String dataStorePath = configSetting.getPropValue(ConfigSettings.DATA_STORE_LOCATION);
            dataStorePath = CaptureUtil.normalizePath(dataStorePath);
            // start to capture the data from the file.
            Dataset dataset = this.dmService.captureData(uploadFileName, upload, extractable, false, collection, dataStorePath, raEnabled, restrictAccess);
            // log the audit event.
            recordAuditEvent(dataset, raEnabled);
            importResponse.setSucceed(true);
            importResponse.setMessage(getText("dataset.import.success", new String[]{dataset.getName()}));
            return SUCCESS;
        } catch (Exception e) {
            logger.error(e);

            importResponse.setSucceed(false);
            importResponse.setMessage(getText("dataset.import.failed"));
            String errorMsg = e.getMessage();
            if (StringUtils.containsIgnoreCase(errorMsg, "not a valid CDM file")) {
                importResponse.setMessage(getText("dataset.import.failed") + ", not a valid Net-CDF file");
            }
            return SUCCESS;
        } finally {
            if (fis != null) {
                try {
                    fis.close();
                } catch (IOException e) {
                    // ignore whatever
                }
            }
        }
    }

    private void recordAuditEvent(Dataset dataset, boolean raEnabled) {
        AuditEvent ev = new AuditEvent();
        ev.setCreatedTime(GregorianCalendar.getInstance().getTime());
        if (raEnabled) {
            ev.setEvent(dataset.getName() + " has been imported into the " + collection.getName() + " associated with a restricted access");
        } else {
            ev.setEvent(dataset.getName() + " has been imported into the " + collection.getName());
        }
        ev.setEventOwner(collection.getOwner());
        ev.setOperator(user);
        recordActionAuditEvent(ev);
    }

    public boolean isRaEnabled() {
        return raEnabled;
    }

    public void setRaEnabled(boolean raEnabled) {
        this.raEnabled = raEnabled;
    }

    public FileImportResponse getImportResponse() {
        return importResponse;
    }

    public void setImportResponse(FileImportResponse importResponse) {
        this.importResponse = importResponse;
    }

    public boolean isExtractable() {
        return extractable;
    }

    public void setExtractable(boolean extractable) {
        this.extractable = extractable;
    }

    public File getUpload() {
        return upload;
    }

    public void setUpload(File upload) {
        this.upload = upload;
    }

    public String getUploadContentType() {
        return uploadContentType;
    }

    public void setUploadContentType(String uploadContentType) {
        this.uploadContentType = uploadContentType;
    }

    public String getUploadFileName() {
        return uploadFileName;
    }

    public void setUploadFileName(String uploadFileName) {
        this.uploadFileName = uploadFileName;
    }
}
