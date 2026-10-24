"""Compatibility entry point. Layouts are now generated from Linux, not Mac."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
KEYS = [(18,2,'1'),(19,3,'2'),(20,4,'3'),(21,5,'4'),(23,6,'5'),(22,7,'6'),(26,8,'7'),(28,9,'8'),(25,10,'9'),(29,11,'0'),(27,12,'OEM_MINUS'),(24,13,'OEM_PLUS'),(12,16,'Q'),(13,17,'W'),(14,18,'E'),(15,19,'R'),(17,20,'T'),(16,21,'Y'),(32,22,'U'),(34,23,'I'),(31,24,'O'),(35,25,'P'),(33,26,'OEM_4'),(30,27,'OEM_6'),(0,30,'A'),(1,31,'S'),(2,32,'D'),(3,33,'F'),(5,34,'G'),(4,35,'H'),(38,36,'J'),(40,37,'K'),(37,38,'L'),(41,39,'OEM_1'),(39,40,'OEM_7'),(50,41,'OEM_3'),(42,43,'OEM_5'),(6,44,'Z'),(7,45,'X'),(8,46,'C'),(9,47,'V'),(11,48,'B'),(45,49,'N'),(46,50,'M'),(43,51,'OEM_COMMA'),(47,52,'OEM_PERIOD'),(44,53,'OEM_2'),(49,57,'SPACE')]

if __name__ == "__main__":
    from generate_from_linux import generate
    print("Using pinned Linux reference; mac_to_klc.py is a compatibility command.")
    generate()
