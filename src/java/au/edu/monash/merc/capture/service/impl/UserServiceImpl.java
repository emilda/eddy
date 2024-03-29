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
package au.edu.monash.merc.capture.service.impl;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import au.edu.monash.merc.capture.dao.impl.UserDAO;
import au.edu.monash.merc.capture.domain.User;
import au.edu.monash.merc.capture.dto.OrderBy;
import au.edu.monash.merc.capture.dto.page.Pagination;
import au.edu.monash.merc.capture.service.UserService;
import au.edu.monash.merc.capture.sso.LoginAuthenticator;
import au.edu.monash.merc.capture.dto.ldap.LdapUser;

@Scope("prototype")
@Service
@Transactional
public class UserServiceImpl implements UserService {

    @Autowired
    private UserDAO userDao;

    @Autowired
    private LoginAuthenticator authenticator;

    public UserDAO getUserDao() {
        return userDao;
    }

    public void setUserDao(UserDAO userDao) {
        this.userDao = userDao;
    }

    @Override
    public void saveUser(User user) {
        this.userDao.add(user);
    }

    @Override
    public void updateUser(User user) {
        this.userDao.update(user);

    }

    @Override
    public void deleteUser(User user) {
        this.userDao.remove(user);
    }

    @Override
    public User getUserById(long id) {
        return this.userDao.get(id);
    }

    @Override
    public User getByUserEmail(String email) {
        return this.userDao.getByUserEmail(email);
    }

    @Override
    public User getByUserUnigueId(String uniqueId) {
        return this.userDao.getByUserUnigueId(uniqueId);
    }

    @Override
    public boolean checkUserUniqueIdExisted(String uniqueId) {
        return this.userDao.checkUserUniqueIdExisted(uniqueId);
    }

    @Override
    public boolean checkUserDisplayNameExisted(String userName) {
        return this.userDao.checkUserDisplayNameExisted(userName);
    }

    @Override
    public boolean checkEmailExisted(String email) {
        return this.userDao.checkEmailExisted(email);
    }

    @Override
    public User login(String username, String password, boolean ldap) {
        return this.authenticator.login(username, password, ldap);
    }

    @Override
    public List<User> getAllActiveUsers() {
        return this.userDao.getAllActiveUsers();
    }

    @Override
    public Pagination<User> getAllUsers(int startPageNo, int recordsPerPage, OrderBy[] orderBys) {
        return this.userDao.getAllUsers(startPageNo, recordsPerPage, orderBys);
    }

    @Override
    public Pagination<User> getAllActiveUsers(int startPageNo, int recordsPerPage, OrderBy[] orderBys) {
        return this.userDao.getAllActiveUsers(startPageNo, recordsPerPage, orderBys);
    }

    @Override
    public Pagination<User> getAllInActiveUsers(int startPageNo, int recordsPerPage, OrderBy[] orderBys) {
        return this.userDao.getAllInActiveUsers(startPageNo, recordsPerPage, orderBys);
    }

    @Override
    public LdapUser verifyLdapUser(String authcatId, String password) {
        return this.authenticator.verifyLdapUser(authcatId, password);
    }

    @Override
    public LdapUser ldapLookup(String cnOrEmail) {
        return this.authenticator.ldapLookup(cnOrEmail);
    }

    @Override
    public User getVirtualUser(int userType) {
        return this.userDao.getVirtualUser(userType);
    }

}
