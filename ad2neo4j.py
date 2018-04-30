#!/usr/bin/env python

########################################
#                                      #
# (ActiveDirectory)-[:Python]->(Neo4j) #
#                                      #
# Version: "First Make it work 1.2     #
#                                      #
########################################

#The Idea is to read almost all objects from a ActiveDirectory
#And put the objects in Neo4j as "nodes" and make a relations with AD groups and there members
#The flow of the program is get all group, computer and person objects from Active Directory 
#and make groupnodes in Neo4j.
#Then get merge all memberOf and primaryGroupID with Neo4j
#(object)-[:memberOf]->(group) and (user/computer)-[:memberOf{based on primaryGroupID]->(groep)
#You need python-ldap3 and Neo4j https://neo4j.com/docs/operations-manual/3.1/installation/

#This one is needed for some issue with Neo4j and Python and "datetime" values.
import datetime
#You can install ldap3 with $pip install ldap3
from ldap3 import Server, Connection, ALL, NTLM 
#You can install neo4j.driver with $pip install neo4j-driver
from neo4j.v1 import GraphDatabase, basic_auth

from neo4j.util import watch
import logging
from sys import stdout
#Debug on/off
#watch("neo4j.bolt", logging.DEBUG, stdout)

#Make a connection with Active Directory
server = Server('{DC ipaddress}', get_info=ALL) 
conn = Connection(server, user="{domain}\\{sAMAccountName}", password="{password}", authentication=NTLM)
conn.bind()

#Make a connection with the Neo4j database
driver = GraphDatabase.driver("bolt://localhost:7687", auth=basic_auth("neo4j", "{password}"))
session = driver.session()

#clear all Nodes from last run
session.run("MATCH (x) WHERE EXISTS(x.extra_info) DETACH DELETE x;")

#Mandatory ActiveDirectory Attributes for merging the relations
mandatory_person_attr = ["primaryGroupID","distinguishedName","memberOf"]
mandatory_computer_attr = ["primaryGroupID","distinguishedName","memberOf"]
mandatory_group_attr = ["primaryGroupToken","distinguishedName","memberOf"]

#Here some functions
#############################Welder##############################
#try to make a welder for AD attributes 2 Neo4j attributes as cypher string
def welder(ad_attr,node_label):
    #This will return a "Cypher" plus "$" string like:
    #CREATE (a:{label} SET a.{AD attribute name} = ${AD attribute name}
    comma = False 
    cypher = "CREATE (a:{}) SET ".format(node_label)
    for x in ad_attr:
        if not comma:
            cypher = cypher + "a.{} = ${} \n".format(x,x)        
            comma = True
        else:
            cypher = cypher + ", a.{} = ${} \n".format(x,x)        
    return cypher 
##################################################################
#End Functions

########################Get AD values and Fill Neo4j Graph DB##################################
#First we "fill" de Neo4j graph Database with ActiveDirectory objects:
#   Persons, Computers and Groups
#Make a list of the attributes you need from the Object you can add more
#But be sure that de attribute exists in the Object (check AD object tab: "Attribute")
#Empty AD Attribute values will NOT create a Neo4j attribute.
#Get the first object: Person
person_attributes = list(set(mandatory_person_attr + [
"givenName"
,"cn"
,"sAMAccountName"
,"objectGUID"
,"objectSid"
,"userAccountControl"
,"uSNCreated"
,"whenCreated"
,"whenChanged"
,"canonicalName"
,"description"
,"info"
,"managedBy"
]))
#Search for Persons and get the attributes needed
conn.search("{DC=domain,DC=local}","(&(objectCategory=person)(objectClass=user))", attributes=person_attributes)
#conn.entries[3].uSNCreated
#Make the Nodes in Neo4j
print(str(len(conn.entries)) + " persons_entries")
for x in conn.entries:          
#    print ("%s  %s  %s" % (x.distinguishedName.value, x.member, x.primaryGroupID))
#    print(welder(person_attributes,"person"))
    #Create a dict with the AD attributes as "keys" and there value extracted from AD.
    neo_advalues_dict = {}    
    for y in person_attributes:
        #There some converting Neo4j Python issue with datatime values so the "datetime" values collected
        #from AD like "whenCreated" or "whenChanged" will be converted to "string".
        if isinstance(x[y].value, datetime.date):
            neo_advalues_dict[y] = str(x[y].value)
        else:
            neo_advalues_dict[y] = x[y].value
    neo_advalues_dict["extra_info"] = "hello world!"
    
    #for z in neo_advalues_dict.keys():
    #    print z + str(type(neo_advalues_dict[z]))
    
    #print(welder(neo_advalues_dict.keys(), "person"), neo_advalues_dict)
    session.run(welder(neo_advalues_dict.keys(), "person"), neo_advalues_dict)
print("persons are made...")
#################################################################

#Make a list of the attributes you need from the Object you can add more
#But be sure that de attribute exists in the Object (check AD object tab: "Attribute")
#Empty AD Attribute values will NOT create a Neo4j attribute.
#Get the second object: Computer
computer_attributes = list(set(mandatory_computer_attr + [
"cn"
,"sAMAccountName"
,"objectGUID"
,"objectSid"
,"userAccountControl"
,"uSNCreated"
,"whenCreated"
,"whenChanged"
,"canonicalName"
,"operatingSystem"
,"dNSHostName"
,"description"
,"info"
,"managedBy"
]))
#Search for Computers and get the attributes needed
conn.search("{DC=domain,DC=local}","(objectCategory=computer)", attributes=computer_attributes)
#Make the Nodes in Neo4j
print(str(len(conn.entries)) + " computer_entries")
for x in conn.entries:          
    #Create a dict with the AD attributes as "keys" and there value extracted from AD.
    neo_advalues_dict = {}    
    for y in computer_attributes:
        #There some converting Neo4j Python issue with datatime values so the "datetime" values collected
        #from AD like "whenCreated" or "whenChanged" will be converted to "string".
        if isinstance(x[y].value, datetime.date):
            neo_advalues_dict[y] = str(x[y].value)
        else:
            neo_advalues_dict[y] = x[y].value
    neo_advalues_dict["extra_info"] = "hello world!"

    #print(welder(neo_advalues_dict.keys(), "computer"), neo_advalues_dict)
    session.run(welder(neo_advalues_dict.keys(), "computer"), neo_advalues_dict)
    
print("computers are made")
#################################################################

#Make a list of the attributes you need from the Object you can add more
#But be sure that de attribute exists in the Object (check AD object tab: "Attribute")
#Empty AD Attribute values will NOT create a Neo4j attribute.
#Get the third object: Group
group_attributes = list(set(mandatory_group_attr + [
"cn"
,"sAMAccountName"
,"objectGUID"
,"objectSid"
,"userAccountControl"
,"uSNCreated"
,"whenCreated"
,"whenChanged"
,"canonicalName"
,"description"
,"info"
,"managedBy"
]))
#Search for group and get the attributes needed
conn.search("{DC=domain,DC=local}","(objectCategory=group)", attributes=group_attributes)
#Make the Nodes in Neo4js
print(str(len(conn.entries)) + " group_entries")
for x in conn.entries:          
    #Create a dict with the AD attributes as "keys" and there value extracted from AD.
    neo_advalues_dict = {}    
    for y in group_attributes:
        #There some converting Neo4j Python issue with datatime values so the "datetime" values collected
        #from AD like "whenCreated" or "whenChanged" will be converted to "string".
        if isinstance(x[y].value, datetime.date):
            neo_advalues_dict[y] = str(x[y].value)
        else:
            neo_advalues_dict[y] = x[y].value
    neo_advalues_dict["extra_info"] = "hello world!"

    #print(welder(neo_advalues_dict.keys(), "group"), neo_advalues_dict)
    session.run(welder(neo_advalues_dict.keys(), "group"), neo_advalues_dict)
print("groups are made")
#################################################################
#Next make relation between Persons/Computers/Groups and Groups
#First create indexes on keys where going to use:
#memberOf for Persons/Computers/Groups
#And PrimaryGroupID for Persons and Computers 
session.run("CREATE CONSTRAINT ON (p:person) ASSERT p.distinguishedName IS UNIQUE;")
session.run("CREATE CONSTRAINT ON (c:computer) ASSERT c.distinguishedName IS UNIQUE;")
session.run("CREATE CONSTRAINT ON (g:group) ASSERT g.distinguishedName IS UNIQUE;")
session.run("CREATE INDEX ON :group(primaryGroupToken);")
session.run("CALL db.awaitIndexes(600);")
#Maybe more indexes etc..
#Now make the relations with members of group
#First the "special" relation with persons and computers and there primaryGroupID
session.run("""MATCH (x) WHERE NOT x:group AND EXISTS(x.extra_info) AND EXISTS(x.primaryGroupID) 
            WITH x, x.primaryGroupID AS pgid 
            MATCH (g:group) WHERE g.primaryGroupToken = pgid 
            MERGE (x)-[:memberof]->(g);""")
print("Person/Computer primarygroup relation is made.")
#And create a match between (x)-[:memberof]->(group)
session.run("""MATCH (x) WHERE EXISTS(x.memberOf) 
            WITH x, x.memberOf AS memof UNWIND memof AS memofx 
            MATCH (g:group) WHERE g.distinguishedName = memofx 
            MERGE (x)-[:memberof]->(g);""")
print("Group/Person/Computer relation with group is made.")

session.close()
