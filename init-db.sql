-- 예약 프로그램 정보
CREATE TABLE ry_mng_reservation (
    res_idx VARCHAR(20) PRIMARY KEY,
    res_title VARCHAR(255) NOT NULL,
    res_desc VARCHAR(1000),
    group_code VARCHAR(20) NOT NULL,
    site_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 예약 회차 정보
CREATE TABLE ry_mng_reservation_part (
    pt_idx INT AUTO_INCREMENT PRIMARY KEY,
    res_idx VARCHAR(20) NOT NULL,
    res_part INT NOT NULL,
    res_part_date DATE NOT NULL,
    res_part_start_time VARCHAR(5),
    res_part_end_time VARCHAR(5),
    res_user_cnt INT DEFAULT 0,
    res_user_cnt_y INT DEFAULT 0,
    res_dl_yn VARCHAR(1) DEFAULT 'N',
    res_dl_yn_msg VARCHAR(100) DEFAULT '예약 가능',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 예약 데이터
CREATE TABLE ry_reservation (
    res_no VARCHAR(20) PRIMARY KEY,
    pt_idx INT NOT NULL,
    res_idx VARCHAR(20) NOT NULL,
    res_status VARCHAR(1) DEFAULT 'N',
    res_name VARCHAR(100) NOT NULL,
    res_mobile VARCHAR(20) NOT NULL,
    res_user_cnt INT NOT NULL,
    res_date DATE,
    res_eml VARCHAR(100),
    res_pri_policy_yn VARCHAR(1) DEFAULT 'N',
    res_group_nm VARCHAR(100),
    res_film_yn VARCHAR(1),
    res_leader_name VARCHAR(100),
    res_leader_mobile VARCHAR(20),
    res_gubun VARCHAR(1),
    res_group_gubun VARCHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 샘플 데이터
INSERT INTO ry_mng_reservation VALUES ('202402270280', '경복궁 한국어 해설 프로그램', '국보 경복궁을 한국어로 해설합니다', 'ROYAL', 'ROYAL', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO ry_mng_reservation_part (res_idx, res_part, res_part_date, res_part_start_time, res_part_end_time, res_user_cnt, res_user_cnt_y) VALUES
('202402270280', 1, '2026-06-20', '10:00', '11:00', 50, 10),
('202402270280', 2, '2026-06-20', '14:00', '15:00', 50, 5),
('202402270280', 3, '2026-06-21', '10:00', '11:00', 50, 20),
('202402270280', 4, '2026-06-21', '14:00', '15:00', 30, 0),
('202402270280', 5, '2026-06-22', '10:00', '11:00', 50, 8),
('202402270280', 6, '2026-06-22', '14:00', '15:00', 50, 0);

INSERT INTO ry_reservation VALUES
('202403265572', 1, '202402270280', 'Y', '홍길동', '010-5066-4068', 59, '2026-06-16', 'hong@example.com', 'Y', NULL, NULL, NULL, NULL, 'Y', 'N', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
