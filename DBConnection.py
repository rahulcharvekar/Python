# importing module
import cx_Oracle 
  
  
# Create a table in Oracle database
try:
  
    con = cx_Oracle.connect(user='rahul',password='oracle',dsn='LAPTOP-OMJLA2FG/ORCL1')
      
    # Now execute the sqlquery
    cursor = con.cursor()
      
    # Creating a table srollno heading which is number
    cursor.execute("create table student(srollno number)")
                      
    print("Table Created successful")
      
except cx_Oracle.DatabaseError as e:
    print("There is a problem with Oracle", e)
  
# by writing finally if any error occurs
# then also we can close the all database operation
finally:
    if cursor:
        cursor.close()
    if con:
        con.close()