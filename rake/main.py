import rake
import psycopg2

conn = psycopg2.connect("dbname=datasets user=abdoo") # connect to database
cursor = conn.cursor() # connect to database

def createTable(name,number):
	n = name+'_result_tags_rake_'+str(number)
	query = ' CREATE TABLE %s' %(n) + '''(
				id SERIAL PRIMARY KEY,
				text_id integer REFERENCES %s''' %(name) + '''(id),
				tag varchar
				);
			'''
	cursor.execute(query)
	conn.commit()

if __name__ == "__main__":
	databases = ['krapivin_text']
	#CREATE DATABASE WITH NAME database_result_tags_rake_n
	for d in databases :
		for i in range(5,16): # FROM 5 TILL 16 (EXCLUDING 16)
		# for i in range(0,1):
			createTable(d,i)
			rake.main(d,i)