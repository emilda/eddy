/*
 * Copyright (c) 2010-2013, Monash e-Research Centre
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

import au.edu.monash.merc.capture.common.LicenceType;
import au.edu.monash.merc.capture.config.ConfigSettings;
import au.edu.monash.merc.capture.domain.Collection;
import au.edu.monash.merc.capture.domain.Licence;
import au.edu.monash.merc.capture.dto.LicenceResponse;
import au.edu.monash.merc.capture.util.CaptureUtil;
import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Controller;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.Map;

/**
 * @author Simon Yu
 *         <p/>
 *         Email: xiaoming.yu@monash.edu
 * @version 1.0
 * @since 1.0
 *        <p/>
 *        Date: 11/03/13 2:57 PM
 */
@Scope("prototype")
@Controller("data.licenceAction")
public class LicenceAction extends DMCoreAction {

    private Licence licence;

    private Map<String, String> licenceMap = new HashMap<String, String>();

    private Logger logger = Logger.getLogger(this.getClass().getName());

    private LicenceResponse licenceResponse;

    @PostConstruct
    public void initLicenceOpts() {
        licenceMap.put(LicenceType.TERN.type(), ActConstants.LICENCE_TERN_LABEL);
        licenceMap.put(LicenceType.USERDEFINED.type(), ActConstants.LICENCE_USER_DEFINED_LABEL);
    }

    /**
     * Show the rights options.
     *
     * @return a String represents SUCCESS or ERROR.                                        lic
     */
    public String showLicenceOptions() {
        try {
            if (licence == null) {
                Licence existedLicence = this.dmService.getLicenceByCollectionId(collection.getId());
                if (existedLicence == null) {
                    licence = new Licence();
                    licence.setLicenceType(LicenceType.TERN.type());
                    licence.setContents(this.configSetting.getPropValue(ConfigSettings.TERN_DATA_LICENCE));
                } else {
                    this.licence = existedLicence;
                }
            }
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("licence.show.options.failed"));
            return ERROR;
        }
        return SUCCESS;
    }

    public String selectLicence() {
        try {
            String requiredLT = licence.getLicenceType();
            //if TERN licence is selected, we just put the tern licence, and return
            if (requiredLT.equals(LicenceType.TERN.type())) {
                this.licence.setContents(this.configSetting.getPropValue(ConfigSettings.TERN_DATA_LICENCE));
                return SUCCESS;
            }

            //find any existed licence if available and the existed licence type is the same as the selected licence type , then we return the existed licence
            Licence existedLicence = this.dmService.getLicenceByCollectionId(collection.getId());
            if (existedLicence != null) {
                String existedLT = existedLicence.getLicenceType();
                if (requiredLT.equals(existedLT)) {
                    licence = existedLicence;
                }
            }

            return SUCCESS;
        } catch (Exception e) {
            logger.error(e);
            addActionError(getText("licence.show.selected.type.failed"));
            return ERROR;
        }
    }

    public String saveLicence() {
        licenceResponse = new LicenceResponse();
        try {
            String licenceContents = licence.getContents();
            String type = licence.getLicenceType();
            if (type.equals(LicenceType.USERDEFINED.type())) {
                if (StringUtils.isBlank(licenceContents)) {
                    licenceResponse.setSucceed(false);
                    licenceResponse.setMsg(getText("licence.must.be.provided"));
                    return SUCCESS;
                }
                if (!CaptureUtil.notGTFixedLength(licenceContents, 4000)) {
                    licenceResponse.setSucceed(false);
                    licenceResponse.setMsg(getText("licence.characters.too.long"));
                    return SUCCESS;
                }
            }
            Licence existedLicence = this.dmService.getLicenceByCollectionId(collection.getId());
            if (existedLicence != null) {
                existedLicence.setContents(licence.getContents());
                existedLicence.setLicenceType(licence.getLicenceType());
                this.dmService.updateLicence(existedLicence);
            } else {
                Collection lcollection = this.dmService.getCollectionById(collection.getId());
                licence.setCollection(lcollection);
                this.dmService.saveLicence(licence);
            }
            licenceResponse.setSucceed(true);
            licenceResponse.setMsg(getText("licence.save.licence.success"));
            return SUCCESS;
        } catch (Exception ex) {
            logger.error(ex);
            licenceResponse.setSucceed(false);
            licenceResponse.setMsg(getText("licence.save.licence.failed"));
            return SUCCESS;
        }
    }

    public Licence getLicence() {
        return licence;
    }

    public void setLicence(Licence licence) {
        this.licence = licence;
    }

    public Map<String, String> getLicenceMap() {
        return licenceMap;
    }

    public void setLicenceMap(Map<String, String> licenceMap) {
        this.licenceMap = licenceMap;
    }

    public LicenceResponse getLicenceResponse() {
        return licenceResponse;
    }

    public void setLicenceResponse(LicenceResponse licenceResponse) {
        this.licenceResponse = licenceResponse;
    }
}
